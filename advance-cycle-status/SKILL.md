---
name: advance-cycle-status
description: Read-only health check of the ADVANCE production server's deploy + 15-min cycle — current deployed tag, the cycle's last Result (success/failed), the next fire time, and the recent journal; optionally whether a specific change is live in the workbook. The reusable verification primitive that /advance-promote composes with after a tag-deploy, and usable standalone to debug "did my deploy land? is the cycle healthy? is X live?". The tag/cycle/journal checks are read-only and need NO lock; the optional live-workbook read is guard-gated (.xlsx), so claim the agent-lock for that part only.
---

# advance-cycle-status

A small, composable read-only check of the server's deploy + cycle health. No
mutations. Use after `/advance-promote` to confirm a deploy, or any time you need
to know whether the production cycle is healthy.

## Core check (read-only — no lock needed)

```bash
ssh -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 '
  cd ~/email_draft_automation
  echo "deployed tag : $(git describe --tags 2>/dev/null)"
  echo "HEAD         : $(git rev-parse --short HEAD)"
  echo "cycle result : $(systemctl show email-draft-automation-cycle.service -p Result --value)"
  echo "cycle active : $(systemctl is-active email-draft-automation-cycle.timer)"
  systemctl list-timers email-draft-automation-cycle.timer --no-pager | sed -n 2p
  echo "--- recent cycle journal ---"
  journalctl -u email-draft-automation-cycle --since "20 min ago" --no-pager | tail -15
'
```
(These carry no mutation keyword, so the agent-lock guard does not gate them.)

## Interpreting
- **`deployed tag`** should equal the `deploy-<date>` tag you promoted (detached
  HEAD at the tag is normal). If it lags, the launcher hasn't run a cycle yet
  (wait) or fetch/checkout failed (see the journal for `cycle_launcher: WARN`).
- **`cycle result` == `success`** → the last cycle ran clean. `failed` →
  investigate the journal (OOM exit 137/124, a task error, etc.).
- **`cycle active` == `active`** → the 15-min timer is running.

## Optional: is a specific change LIVE? (lock-gated — reads the workbook)

Reading the live workbook is `.xlsx`-guard-gated, so claim the lock first:
```bash
python3 tools/agent_lock.py claim "cycle-status workbook read"
ssh -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 \
  'cd ~/email_draft_automation && .venv/bin/python3 - <<PY
from openpyxl import load_workbook
import os
wb = load_workbook(os.path.expanduser("~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx"),
                   read_only=True, data_only=True)
# ... read the sheet/cell that proves your change is live ...
PY'
python3 tools/agent_lock.py release
```

## Composes with
- **[/advance-promote](../advance-promote/SKILL.md)** — run this right after to verify the tag landed.
- **[/advance-lock](../advance-lock/SKILL.md)** — for the optional workbook read.
- For deeper live checks, run `tools/layer_c_smoke.py` on the server (the nightly drift detector).
