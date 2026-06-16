---
name: advance-ship
description: Ship an ADVANCE task — push the current task/<id> branch and open a Merge Request set to AUTO-MERGE on green CI (the multi-agent workflow; docs/adr/0004). Uses GitLab push-options (merge_request.create + merge_when_pipeline_succeeds + remove_source_branch) so the MR merges itself the moment the hermetic CI passes — no manual merge click. Run the relevant local test gate FIRST. Invoke when a task's code is committed and ready to land on main. Lands on main automatically on green, but deploy stays tag-gated — nothing reaches production until /advance-promote pushes a deploy tag.
---

# advance-ship

Push your task branch and open an MR that **auto-merges the moment CI is green**
— so no one has to click merge for routine agent work. Production is unaffected
until you separately `/advance-promote` (push a deploy tag).

## Pre-flight (do not skip)

```bash
git rev-parse --abbrev-ref HEAD     # must be task/<id>, NOT main
git status -s                        # everything you intend is committed
git fetch origin && git rebase origin/main   # ship on a CURRENT base, not stale
```
Run the **test gate for what you touched** (see CLAUDE.md "Test certification");
at minimum `make test-a`. CI re-runs it, but failing locally wastes a cycle.

## Ship (push + auto-merging MR)

```bash
git push -u origin HEAD \
  -o merge_request.create \
  -o merge_request.target=main \
  -o merge_request.title="<conventional commit subject>" \
  -o merge_request.description="<what + why; note touched personas if any>" \
  -o merge_request.merge_when_pipeline_succeeds \
  -o merge_request.remove_source_branch
```

- **Green CI → GitLab auto-merges** the MR and deletes the branch. You never click merge.
- **Red CI → the MR stays open/blocked** (auto-merge won't fire). Fix, push again.
- This is the project's chosen auto-merge model (push-option; no API token). It
  covers every MR shipped this way.

## Watching for the merge (no glab / API token)

There's no `glab` or GitLab API token on this machine, so poll the remote refs —
auto-merge **deletes the source branch** (`remove_source_branch`) and advances
`main` when CI goes green. A backgroundable watcher (`run_in_background: true`):

```bash
cd ~/dev/<task-id>/email_draft_automation
BASE=$(git ls-remote origin -h refs/heads/main | awk '{print $1}')
for i in $(seq 1 60); do
  out=$(git ls-remote origin -h refs/heads/main "refs/heads/task/<task-id>")
  main=$(printf '%s\n' "$out" | awk '/refs\/heads\/main$/{print $1}')
  task=$(printf '%s\n' "$out" | awk '/task\/<task-id>$/{print $1}')
  [ -z "$task" ] && { echo "MERGED ✅ main=$main"; exit 0; }   # source branch gone
  [ "$main" != "$BASE" ] && { echo "MAIN MOVED ✅ main=$main"; exit 0; }
  sleep 20
done
echo "TIMEOUT — CI still running or RED (MR stays open)"
```

Branch still present + `main` unmoved after the timeout → CI is slow or red; open
the MR URL the push printed to check the pipeline. (CI runs `test-a` + `test-b` +
`test-headers`, a few minutes.)

## After it merges
- Dispose your clone: `rm -rf ~/dev/<task-id>`.
- To put the merged change **into production**, run **[/advance-promote](../advance-promote/SKILL.md)**
  (push a `deploy-<date>` tag). Merging to `main` does NOT deploy.

## Safety
- **Never ship from a stale base** — rebase on `origin/main` first (a stale base
  silently corrupts the diff + analysis; cf. the 2026-06-08 incident).
- **Never from the OneDrive tree or a shared clone** — ship from your isolated
  clone (`/advance-new-task`).
- CI runs `test-a` + `test-b` + `test-headers`. If you changed draft-creation
  paths, also run their `make test-b-*` locally (not yet all in CI).
- Don't bypass a red pipeline by merging manually — red means stop.
