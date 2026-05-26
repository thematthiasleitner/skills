---
name: graph-sentitems-scan
description: Scan a Microsoft Graph SentItems mailbox folder reliably. Avoids two non-obvious Graph traps that have cost hours of debugging — the $orderby slow-sort and the pagination-duplicate infinite loop. Invoke whenever you need to walk SentItems messages by date range (e.g. for the ADVANCE sent_log backfill, mailbox auditing, or any historical email scan that can't rely on Phase-1 tagging).
---

# Microsoft Graph SentItems Scan — Two Traps + Correct Recipe

Discovered 2026-05-26 during the ADVANCE `sent_log` backfill. The naive `GET /mailFolders/SentItems/messages?$filter=sentDateTime…&$orderby=sentDateTime asc` query has **two failure modes** that together can hang a job for hours and produce 30,000 phantom messages from a 1,500-message mailbox.

---

## Trap 1 — `$orderby` triggers a server-side sort

Graph's SentItems folder doesn't have an index suitable for `$orderby sentDateTime`. Adding `$orderby` to any filter that returns >16 messages forces a backend sort that can take **30+ minutes per chunk**. The httpx client appears to hang; there is no error, just silence. Memory grows slowly as bytes trickle in.

**Symptom:** First few small chunks (≤16 msgs each) complete in <1s. The first chunk with >100 messages then hangs 25+ minutes. Process is alive (`ps`), connection ESTABLISHED to `20.190.183.x`, no errors logged. CPU low, memory creeping up.

**Fix:** Omit `$orderby` entirely. Order doesn't matter for batch scans — caller can sort the JSONL after.

---

## Trap 2 — pagination loops on duplicates (no `$orderby`)

Without `$orderby`, Graph paginates the result set using an opaque skip-token. After the real results are exhausted, the `@odata.nextLink` continues to return — but it returns the **same trailing batch of ~10 messages indefinitely**. Naively iterating `while next_link:` produces an infinite stream of duplicates. Verified: 110 unique messages got reported as 18,110 across 1,800+ pages before the loop was caught.

**Symptom:** Pages stream in at ~5/sec, each adds 10 messages, message count grows linearly forever, memory creeps up by ~4 MB/min. No errors. Will not stop on its own.

**Fix:** Track seen `message_id`s in a `set`; break the pagination loop as soon as a page contains **zero new IDs**.

---

## The correct recipe

```python
def scan_sent_chunk(mail, since_iso: str, until_iso: str, page_size: int = 100):
    """Walk a 3-day window of SentItems. Returns dedup'd list of message dicts."""
    out, seen = [], set()
    params = {
        "$top": page_size,
        "$filter": f"sentDateTime ge {since_iso} and sentDateTime lt {until_iso}",
        "$select": "id,subject,sentDateTime,toRecipients,conversationId",
        # NO $orderby — it triggers slow server sort.
    }
    url = f"/users/{mail.mailbox}/mailFolders/SentItems/messages"
    page = 0
    while url:
        resp = mail._request("GET", url, params=params)
        data = resp.json()
        page += 1
        page_new = 0
        for msg in data.get("value", []):
            mid = msg.get("id") or ""
            if mid in seen:
                continue
            seen.add(mid)
            page_new += 1
            out.append(msg)
        # Trap 2 fix: break when a page yields zero new message IDs.
        if data.get("value") and page_new == 0:
            break
        nxt = data.get("@odata.nextLink")
        if not nxt:
            break
        url = nxt.replace(mail.base_url, "")
        params = {}  # nextLink carries its own params
    return out
```

## Additional hardening

- **Walk the date range in 3-day chunks** at most. Larger chunks are more likely to hit Graph's gateway-timeout 503s.
- **Wrap each request in a 503/504 retry** with exponential backoff (5 → 10 → 20 → 40 → 60s, max 5 retries). Production `_request` only retries 429.
- **Persist per-chunk JSONL to disk immediately after each chunk completes** (not at the end of the whole scan). Combined with a manifest of done chunks, you get crash-safe `--resume`. See `crash-safe-batch-pipeline` skill.

## Lazy body fetch

If you need message bodies, **do not** add `body` to `$select` on the chunk scan — that 10× the response size and increases 503 risk. Fetch bodies individually only for messages you actually need:

```python
def fetch_body_and_created(mail, message_id: str):
    resp = mail._request("GET", f"/users/{mail.mailbox}/messages/{message_id}",
                        params={"$select": "body,createdDateTime"})
    data = resp.json()
    return (data.get("body") or {}).get("content") or "", data.get("createdDateTime") or ""
```

`createdDateTime` is the draft-creation timestamp (independent of `sentDateTime`) — useful for recovering wiped workbook stamps.

## Working reference

See `email_draft_automation/tools/backfill_sent_log_history.py` — that's the production implementation that survived all the failure modes above. The `_scan_chunk_metadata` function is the canonical pattern; copy-paste from there for new tools.

## Anti-patterns to avoid

- ❌ `$filter` over a 90-day window with `$expand=singleValueExtendedProperties(...)`: triggers gateway 503s reliably.
- ❌ `$orderby sentDateTime asc` on any window larger than 1 day.
- ❌ Trusting `@odata.nextLink` to terminate. It doesn't (without `$orderby`).
- ❌ Reading bodies inline during the scan. Always defer.
