---
name: crash-safe-batch-pipeline
description: Design a long-running batch job so it survives mid-run crashes (503s, OOM, network drops, killed processes) without restarting from scratch. Decomposes the job into independent phases that each persist their output to disk before the next phase starts. Invoke when you're about to write or refactor any pipeline that walks a large dataset (mailbox scan, API enrichment, bulk export) where a failure midway would otherwise discard hours of work.
---

# Crash-Safe Batch Pipeline — 4-Phase Decomposition

Hard-won lesson from the ADVANCE `sent_log` 90-day backfill: the first naive implementation accumulated 1150 messages in memory across 30 chunks and wrote a single CSV at the end. It died on chunk 8 (503 + retry exhaustion). **Zero output**. Restarting meant re-scanning all 7 already-done chunks. Three failed runs later, the design was wrong — not the bug.

The fix: decompose into phases that each commit their work to disk immediately. Then `--resume` becomes trivial.

---

## The pattern (4 phases)

```
Phase A: SCAN     — walk source data in chunks → write per-chunk JSONL + manifest
Phase B: MATCH    — local-only filter / transform → write matched.jsonl
Phase C: FETCH    — expensive per-item enrichment → write rows.jsonl
Phase D: COMMIT   — write final output (CSV / sheet / DB)
```

Each phase reads from the previous phase's disk artefacts, never from memory. Each phase can be re-run independently. Phase A supports `--resume` via a manifest file that lists completed chunk keys.

---

## Concrete scaffolding

```python
# Phase A
def scan_phase(client, since, resume=False):
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    done_keys = {c["key"] for c in manifest["chunks"] if c.get("done")}
    for chunk_window in iter_windows(since):
        key = chunk_window.key()
        if resume and key in done_keys:
            logger.info("skip %s (already done)", key)
            continue
        items = expensive_scan(client, chunk_window)  # may 503 mid-run
        # Write JSONL IMMEDIATELY before updating manifest.
        chunk_path = CHUNKS_DIR / f"chunk_{key}.jsonl"
        with chunk_path.open("w") as f:
            for it in items:
                f.write(json.dumps(it) + "\n")
        manifest["chunks"].append({"key": key, "count": len(items), "done": True})
        _write_manifest(manifest)  # atomic write via tmp + rename

# Phase B — pure local, no network
def match_phase(rules):
    matched = []
    for chunk_path in sorted(CHUNKS_DIR.glob("chunk_*.jsonl")):
        for line in chunk_path.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                if hit := apply_rules(item, rules):
                    matched.append({**item, **hit})
    MATCHED_PATH.write_text("\n".join(json.dumps(m) for m in matched))

# Phase C — expensive per-item work; one round-trip per match
def fetch_phase(client):
    matched = [json.loads(l) for l in MATCHED_PATH.read_text().splitlines() if l.strip()]
    rows = []
    for i, m in enumerate(matched, 1):
        extra = expensive_enrich(client, m)
        rows.append({**m, **extra})
        if i % 10 == 0:
            logger.info("fetched %d/%d", i, len(matched))
    ROWS_PATH.write_text("\n".join(json.dumps(r) for r in rows))

# Phase D — commit to authoritative store; supports --dry-run preview
def commit_phase(target, dry_run=False):
    rows = [json.loads(l) for l in ROWS_PATH.read_text().splitlines() if l.strip()]
    write_preview_csv(rows, LOGS_DIR / f"preview_{ts()}.csv")
    if dry_run:
        return
    append_to_target(target, rows)  # dedupe by primary key
```

---

## Hard invariants that make this work

1. **Atomic disk writes per chunk.** Either the chunk JSONL is complete or it doesn't exist. Use tmp-file-then-rename for both chunk files and the manifest. A killed process never leaves a half-written chunk that the next run mistakes for done.

2. **Manifest is the source of truth for "what's done".** Even if a chunk JSONL exists on disk, `--resume` skips it only if the manifest entry says `done: true`. This lets you blow away the manifest to force a re-scan without deleting the JSONL backups.

3. **Each phase reads only from disk.** Never pass in-memory results between phases. A new process starting cold should be able to resume any later phase from disk artefacts alone.

4. **Phase C uses individual requests, not batch.** Resist the urge to batch the enrichment. One slow GET per matched item is cheaper than one batch GET that 503s halfway and loses everything. Plus a single-item failure is just a `try/except` away from a continue.

5. **Phase D writes a preview CSV before mutating the target.** Always. `--commit` is opt-in. Lets a human eyeball the diff before it lands.

6. **Dedupe on commit by stable primary key.** Re-running Phase D shouldn't double-write. For email-scans the natural key is `message_id`.

---

## CLI design

```
--phase {scan,match,fetch,commit,all}  default: all
--resume      Phase A only: skip chunks whose manifest says done
--commit      Phase D only: actually write to target (opt-in)
--days N      Phase A only: lookback window
--workbook P  Path overrides where relevant
```

Per-phase invocation lets you re-run only what changed:
- New matching rule? `--phase match` then `--phase fetch` (skip scan).
- New enrichment field? `--phase fetch` then `--phase commit`.
- Crash mid-scan? `--phase scan --resume`.

---

## Logging discipline

- Use a **dual sink**: print to stdout (visible during `tail -f`) AND append to a persistent `progress.log` in the chunks directory. The progress log survives setsid detachment and SSH disconnect.
- Log per-chunk (`chunk N/M completed: K items, total so far: T`), not per-item — but for the slowest pages within a chunk, add a per-page log to make sub-chunk progress visible (else a multi-minute chunk looks like a hang).
- `print(line, flush=True)` to defeat stdout buffering. Without `flush`, a `> log` redirect shows nothing until process exit.

---

## When to use this pattern

Use it when **any** of:
- Total runtime > 5 minutes (long enough that mid-run failures are likely).
- External network calls in a loop (one bad chunk can sink the run).
- Operating in a hostile env (server with OOM risk, flaky VPN, shared workbook locks).
- Output is destructive (writing to a live sheet / DB) — preview-then-commit gates safer.

Don't use it when:
- The job is < 30 seconds and fully in-memory (overkill).
- There's no per-item granularity (you can't make resume work).

---

## Reference implementation

`email_draft_automation/tools/backfill_sent_log_history.py` is the production version. Phases A–D are clearly delimited; the manifest + JSONL pattern is intact; the `--resume` flag works; the preview-then-commit pattern is enforced. Copy it as a template when scaffolding a new pipeline.
