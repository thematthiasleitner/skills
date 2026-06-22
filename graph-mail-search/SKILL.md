---
name: graph-mail-search
description: Mailbox-wide Microsoft Graph $search — find every message matching a term (participant email, surname, a bad link) across ALL folders of a shared mailbox at once (Drafts root, Sent Items, Archive, Deleted Items), not just one subtree. Read-only, one bundled script. Use to answer "is there ANY mail to/from participant X anywhere?", to locate a manually-composed draft that lives OUTSIDE Drafts/hardcoded (so graph-drafts-tree can't see it), or to confirm an email truly vanished from the shared mailbox before telling someone the automation didn't delete it. Catches the "where did my email go" / "did the pipeline eat it" support question. Callable standalone or as the wide-net scan step inside a draft/mail diagnosis. Complements graph-drafts-tree (Drafts/hardcoded subtree, body-grep) and graph-sentitems-scan (SentItems by date only).
---

# Microsoft Graph mailbox-wide search

Read-only walker that runs a single Graph `$search` over a mailbox's **whole**
message store and reports each hit's folder, draft/sent state, timestamps,
from/to, and subject. The wide net that the two narrower sibling skills don't
cast.

## When to use

- "Where did email X go? / Did the automation delete my sent mail?" — search
  the term across the whole shared mailbox and show every hit (or prove zero).
- A participant's row looks empty / something seems missing and you need to know
  whether **any** draft or sent copy for them exists anywhere.
- You suspect a **manually-composed** draft sitting in the Drafts root or a
  custom folder — `graph-drafts-tree` only walks `Drafts/hardcoded`, so it would
  miss it; this won't.
- Post-fix sweep: `--expect-empty "bad-link"` exits 1 if any message still
  matches (assert the mailbox is clean), mirroring `graph-drafts-tree --grep`.

## Quick start

Run where a live Graph token exists (usually the ADVANCE server; local
`ms_token.json` copies are usually stale — see Preconditions):

```bash
ssh leitneruser@10.40.41.88
cd ~/email_draft_automation && set -a && source .env && set +a
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/mail_search.py "e.bruder01@bluewin.ch"
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/mail_search.py "Bruder" "e.bruder01@bluewin.ch"
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/mail_search.py --expect-empty "SV_oldlink"
```

(scp the script to the server's `/tmp` first if running there; delete after.)

- Positional args = one or more search terms (email, surname, link, subject
  fragment). Each is searched independently and printed in its own block.
- Search both the **address** and the **surname** — `$search` indexes recipients
  and body, but a body that uses only a first name won't match the address.
- `--expect-empty` → exit 1 if ANY term has hits; else exit 0.

## Why a script (the encoded traps)

- `$search` on `/messages` **requires the `ConsistencyLevel: eventual` header**
  (passed via `_request(consistency="eventual")`). Omit it and Graph may 400 or
  silently ignore the term — a false "0 found".
- `$search` reaches every **visible** folder but **not** the Recoverable Items
  dumpster ("Recover items recently removed from this folder"). A hard-deleted
  message reads as absent. The script's TOTAL line says so — repeat that caveat
  when you report "nothing found", and point the user at the dumpster + their
  **personal** Sent folder (shared-mailbox sends often land there, not in the
  shared mailbox).
- Shared mailboxes: this searches the **shared** mailbox only. Mail a colleague
  sent from their own account won't appear — that needs access to *their*
  mailbox, which the project token does not grant.

## Preconditions

- A working Graph token reachable via `build_graph_service_from_env()`
  (env: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_MAILBOX`; cache `ms_token.json`).
  Local caches are usually dead (`MissingGraphToken`) and device-code re-auth is
  permanently blocked — run on the server, where the cycle keeps the token fresh.
  Run **`advance-graph-health`** first if Graph calls fail.
- SSH to the server needs the passphrase-protected key loaded — see
  **`request-ssh-access`**.
- Read-only — needs no agent-lock; plain SSH reads pass the guard.

## Composes with

- **graph-drafts-tree** — narrow the wide hit down inside the `Drafts/hardcoded`
  subtree (counts/subjects) once this tells you a draft exists.
- **graph-sentitems-scan** — date-ranged SentItems walk when you need the full
  sent history, not just term matches.
- **advance-graph-health** — run first if the token might be dead.
- **request-ssh-access** — load the server SSH key before running there.
- **audit-hardcoded-drafts** — deep per-draft correctness audit after locating.

## Test

Hermetic: `python3 -m pytest ~/.claude/skills/graph-mail-search/test_mail_search.py -q`
(drives the pure `search()` core with fake fetchers — folder-name resolution,
counting, empty/None tolerance, sparse-message formatting; no network).
