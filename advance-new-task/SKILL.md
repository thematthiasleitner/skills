---
name: advance-new-task
description: Start an ADVANCE coding task in an isolated, CURRENT git clone off origin/main (the multi-agent workflow; docs/adr/0004). Wraps scripts/new-agent.sh — fresh clone OUTSIDE OneDrive at ~/dev/<task-id>/email_draft_automation, branch task/<task-id>, secrets + a private preview-workbook copy + .venv. Invoke at the START of any email_draft_automation coding task, or whenever an agent finds itself in the OneDrive tree / a shared clone and must move to an isolated one. Read-only/local — low risk.
---

# advance-new-task

Spin up an **isolated, current** workspace for a coding task. Every agent works
in its OWN clone off `origin/main` — never the OneDrive tree or a shared clone
(that caused the 2026-06-05 cross-agent commit + the 2026-06-08 stale-base
near-miss). See [docs/adr/0004-isolated-clones-protected-main-deploy.md](../../docs/adr/0004-isolated-clones-protected-main-deploy.md).

## Steps

1. **Pick a short task-id** (kebab-case): e.g. `facility-signout`, `zoom-urls`.
2. **Create the workspace:**
   ```bash
   scripts/new-agent.sh <task-id>
   ```
   This clones off `origin/main` to `~/dev/<task-id>/email_draft_automation`,
   branches `task/<task-id>`, copies `.env` + `qualtrics/qualtrics_env.sh` + a
   **private** preview-workbook copy (NOT `ms_token.json`, NOT a live-workbook
   symlink), and builds `.venv`.
3. **Launch the agent IN the clone** (so its hooks bind to the clone):
   ```bash
   cd ~/dev/<task-id>/email_draft_automation && ADVANCE_AGENT_ID=<task-id> claude
   ```
4. **Sanity-check the base is current + clean:**
   ```bash
   git log --oneline -1 origin/main   # recent, not a week old
   git status -sb                       # clean, on task/<task-id>
   make test-a                          # hermetic gate passes
   ```

## When done
- Ship with **`/advance-ship`** (push + auto-merging MR).
- Then **`/advance-promote`** to deploy a merged change (tag).
- Dispose the clone after merge: `rm -rf ~/dev/<task-id>`.

## Already in the OneDrive tree / a shared clone, mid-work?
Don't continue there. Follow
[docs/agent_onedrive_to_gitlab_migration.md](../../docs/agent_onedrive_to_gitlab_migration.md)
("Carrying forward work you'd already started") to move the work onto a fresh
clone before continuing.

## Notes
- The agent-lock ([/advance-lock](../advance-lock/SKILL.md)) is still required
  before LIVE/server ops — isolation fixes *code* collisions only.
- The OneDrive tree is reference-only (workbooks via bisync); never run git there.
