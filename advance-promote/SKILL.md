---
name: advance-promote
description: Deploy merged ADVANCE code to production by pushing a promote tag (tag-deploy; docs/adr/0004 Phase 3). The server's cycle_launcher fetches + checks out the latest deploy-<date> tag at its next 15-min cycle, then the export runs the new code — no SSH, no passphrase. HIGH-RISK (changes live behaviour) — propose via AskUserQuestion, NEVER silently invoke; explicit consent required. Invoke when a change is merged to main and the user wants it live. Claim the agent-lock for the post-deploy live verification. Replaces the manual push+pull dance (now break-glass in /advance-deploy).
---

# advance-promote

Ship a **merged** change to production by tagging it. The server pulls the tag
itself; you never SSH or type a passphrase.

> **High-risk: this changes live behaviour.** Propose via `AskUserQuestion` and
> get explicit consent (or the user typing `/advance-promote`) before tagging.

## Pre-flight
```bash
git fetch origin --tags
git log --oneline -1 origin/main      # the change you want live IS merged here
# Tagging HEAD deploys EVERY merged commit since the last deploy — not just yours.
# Surface the ride-along delta and confirm it's all meant to go live:
LATEST=$(git tag -l 'deploy-*' --sort=-version:refname | head -1)
git log --oneline "$LATEST"..origin/main    # ← everything here ships if you tag HEAD
```
Only deploy what's on `origin/main` (it passed CI + landed via MR). Never tag a
feature branch or a stale commit.

> **Ride-along check (do not skip).** `deploy-*` tags `origin/main` HEAD, so it
> ships **all** commits in `$LATEST..origin/main`, including other agents' merged
> work. If the delta contains changes that aren't yours / aren't ready, STOP and
> surface them via `AskUserQuestion` before tagging — deploying someone else's
> change is their call (cf. the 2026-06-12 zoom_url session; the cadence-deferred
> note in `project_zoom_courses_golive_plan`). You generally **cannot** isolate
> just your commit if another merged ahead of you (it's an ancestor of your merge).
>
> **Promote may be unnecessary.** If your change was a *direct live edit* — a
> Qualtrics survey API mutation, or a server-side workbook edit — it is **already
> live** and the MR only lands an inert script/record. Promoting then does nothing
> for your task but still ships the whole delta. Confirm the change actually needs
> code on the server before tagging.

## Promote (push the tag)
```bash
TAG="deploy-$(date +%F)"
# if a tag for today already exists, suffix it: deploy-$(date +%F)b, ...c
git tag "$TAG" origin/main && git push origin "$TAG"
git tag -l 'deploy-*' --sort=-version:refname | head -1   # confirm yours sorts FIRST
```
The server's `cycle_launcher.sh` picks up the highest `deploy-*` tag at the start
of its next cycle (≤15 min), checks it out, and runs the export on it.

## Verify

After the next cycle (~15 min), run **[/advance-cycle-status](../advance-cycle-status/SKILL.md)**
to confirm the deployed tag == your tag, the cycle's last Result == `success`, and
(for a live-data change) that it's visible in the workbook. That skill handles the
read-only checks (no lock) and the lock-gated workbook read — so promote stays a
thin "push the tag" step that composes with it.

## Rollback
Tag a previous good commit with a NEWER `deploy-*` tag and push it — the next
cycle reverts to it (the launcher always takes the latest tag). Or pause
auto-deploy: set `ADVANCE_AUTODEPLOY=0` on the server (see
[docs/deploy_server_autopull_runbook.md](../../docs/deploy_server_autopull_runbook.md)).

## Notes
- Server setup (deploy token, units) is the one-time rollout in the runbook above.
- For an EMERGENCY when auto-deploy is unavailable, the manual push+pull dance is
  the break-glass `/advance-deploy` skill.
- Don't promote a change that hasn't been live-verifiable; pair risky promotes
  with a Layer C check (`tools/layer_c_smoke.py`) after the cycle.
