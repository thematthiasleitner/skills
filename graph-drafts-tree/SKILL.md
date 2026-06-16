---
name: graph-drafts-tree
description: Print a Microsoft Graph mail Drafts folder tree with per-folder item counts, optional message subjects, and an optional body grep that exits non-zero on hits — read-only, bundled script. Use when verifying what drafts exist where (e.g. ADVANCE Drafts/hardcoded or _test_drafts), sweeping ALL draft bodies for a bad pattern (old survey link, placeholder, wrong URL) before/after a fix, or answering "is template X's draft really in folder Y". Callable standalone or as the scan step inside a draft-fix task.
---

# graph-drafts-tree

Read-only walker for a Graph mailbox Drafts subtree. One bundled script,
three modes: tree+counts, +subjects, +body-grep.

## Quick start

Run where a live Graph token exists (usually the ADVANCE server; local
`ms_token.json` copies are often stale):

```bash
ssh leitneruser@10.40.41.88   # or any clone with a working token
cd ~/email_draft_automation && set -a && source .env && set +a
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/drafts_tree.py                  # Drafts/hardcoded tree
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/drafts_tree.py _test_drafts hardcoded --subjects
PYTHONPATH=$HOME .venv/bin/python3 <skill>/scripts/drafts_tree.py --grep SV_42W7wVwedBnaUB0
```

(scp the script to the server's `/tmp` first if running there; delete after.)

- Positional args = folder segments under `Drafts` (default `hardcoded`).
- `--grep PATTERN` prints every draft whose body contains PATTERN
  (path, recipient, subject, count) and **exits 1 on any hit** — so a
  post-fix re-scan asserting cleanliness is just "exit 0".

## Why a script (the encoded traps)

- mailFolder's count property is **`totalItemCount`** — `totalChildItemCount`
  does not exist and 400s the request.
- Sweep the **whole** subtree, never just the folder a task names: the
  2026-06-11 old-link fix found its only real straggler in a folder nobody
  had mentioned (memory: `feedback-sweep-whole-drafts-tree`).
- `walk()` scans the named root folder's **own** messages too, not only its
  children — so scoping `--grep` at a leaf folder is safe. (It used to walk
  children only; a leaf-scoped grep then scanned nothing and falsely read
  clean. Fixed 2026-06-16, regression-tested in `test_drafts_tree.py`.)

## Preconditions

- A working Graph token reachable via `build_graph_service_from_env()`
  (env: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_MAILBOX`; cache `ms_token.json`).
- Read-only — needs no agent-lock; plain SSH reads pass the guard.

## Composes with

- **audit-hardcoded-drafts** — this is the lightweight "what's where" scan;
  that skill does deep per-draft correctness auditing.
- **graph-sentitems-scan** — sibling for SentItems (date-ranged, paginated).
- **advance-graph-health** — run that first if Graph calls fail with
  `MissingGraphToken`.

## Test

Hermetic: `python3 -m pytest ~/.claude/skills/graph-drafts-tree/test_drafts_tree.py -q`
(walk/format/grep logic with fake fetchers; no network).
