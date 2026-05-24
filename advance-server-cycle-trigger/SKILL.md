---
name: advance-server-cycle-trigger
description: Trigger a one-shot manual export cycle on the ADVANCE production server (in-between the 15-min auto-cron-cycles). SSH-runs qualtrics/export_responses_to_contacts.py with QUALTRICS_WORKBOOK_MODE=live, prints exit code + log tail, then optionally re-reads workbook columns of interest. **High-risk (mutates live workbook + may write drafts to live mailbox) — DO propose via AskUserQuestion when the user wants immediate workbook materialisation, but NEVER silently invoke. Explicit user consent required.** Surface this skill right after /advance-deploy completes (to make just-pulled changes take effect without waiting 15 min), OR when the user mentions wanting to "see the change in the workbook now", OR when the user observes a new Qualtrics response and wants it materialised immediately.
tools: Bash, Read
---

# ADVANCE Server Cycle Trigger Skill

You trigger an immediate one-shot manual export cycle on the ADVANCE production
server, between the auto-scheduled 15-min cron cycles. This materialises any
fresh Qualtrics survey responses (or fresh code changes) into the live workbook
WITHOUT waiting up to 15 min for the next auto-cycle.

**This skill mutates the live workbook + may write to the live mailbox draft folders — high-risk.**

**Discovery vs invocation pattern** (per project CLAUDE.md "Skill-suggestion checkpoint"):

- ✅ **DO surface this skill via `AskUserQuestion`** in deploy-then-verify
  contexts (post-`/advance-deploy`, or when the user mentions wanting to
  see workbook changes immediately).
- ❌ **NEVER silently invoke** without explicit consent. The cycle takes ~60-145s,
  writes to the live workbook, and may trigger downstream draft creation in the
  shared mailbox visible to teammates.
- ✅ **If the user types `/advance-server-cycle-trigger`** or approves an
  AskUserQuestion proposal, that IS explicit consent — proceed.

The AskUserQuestion proposal should:
- Note the expected duration (~60-145s)
- Note the side effects ("rewrites live workbook + may create drafts in the
  shared mailbox if new participants meet draft criteria")
- Offer at least one alternative ("alternatively: wait up to 15 min for the
  next auto-cycle")

**Composability:** typically runs right after `/advance-deploy` (to make a
just-pulled change take effect immediately) or after the user observes a new
facility submission in Qualtrics they want to see in the workbook now.

---

## When to propose (then await explicit consent)

- User has just deployed a change and wants immediate workbook materialisation
- User just submitted a Qualtrics response and wants it in the workbook NOW
- A previous cycle FAILed and the user wants to verify the next on-demand run
  succeeds before relying on the cron

## When NOT to propose

- If user just asked "Did the last cycle run?" — propose journal-reading
  instead. Don't propose triggering a new cycle just to answer a status question.
- If the auto-cycle is currently running (race risk). Check
  `systemctl status email-draft-automation-cycle.service` first; if active,
  suggest waiting 3 min and re-asking.
- If the systemd timer is currently STOPPED for manual mode
  ([[reference-manual-cycle-control]]) — the manual maintenance pattern
  bypasses the timer for a reason. Surface the manual-mode-active warning instead.

## When to invoke directly (no AskUserQuestion needed)

- The user typed `/advance-server-cycle-trigger` in the chat — explicit consent
- The user already approved a multi-step plan that included a cycle trigger

---

## Workflow

### Step 0: Safety check

```bash
ssh leitneruser@10.40.41.88 'echo "$PASS" | sudo -S systemctl is-active \
  email-draft-automation-cycle.service 2>/dev/null'
```

- `active`: a cycle IS currently running. WAIT — don't trigger now. Report to
  user + suggest re-invoking in 3 min.
- `inactive`: safe to proceed.
- `unknown`/error: the systemd timer state is weird (manual mode?). Refuse +
  surface to user.

### Step 1: Trigger

Use [_trigger.sh](_trigger.sh) (in this skill folder):

```bash
ssh leitneruser@10.40.41.88 'bash -s' < ~/.claude/skills/advance-server-cycle-trigger/_trigger.sh
```

The script:
- Sources `qualtrics_env.sh`
- Unsets QUALTRICS_WORKBOOK_PATH (use the live workbook by default)
- Sets `QUALTRICS_WORKBOOK_MODE=live` + `QUALTRICS_RUNTIME_STATUS=server`
- Runs `timeout 180 .venv/bin/python3 -u qualtrics/export_responses_to_contacts.py`
- Captures tail -15 of output
- Reports exit code

### Step 2: Report

Pretty-print:
- Cycle duration (parse from log)
- EXIT code
- Number of facility responses processed (parse from log: lines matching
  `f_ty_2_con` / `list_rooms`)
- If EXIT≠0: paste last 30 lines + suggest server-side diagnosis pattern
  per [email_draft_automation CLAUDE.md "Server-side diagnosis"](../../../../Users/matthias/Library/CloudStorage/OneDrive-UniversitédeGenève/RA HORIZON/email_draft_automation/CLAUDE.md)

### Step 3: Optional follow-up workbook inspection

If the user wants to see specific workbook columns after the cycle:

```bash
ssh leitneruser@10.40.41.88 'cd ~/email_draft_automation && .venv/bin/python3 -c "
from openpyxl import load_workbook
wb = load_workbook(\"Qualtrics_ADVANCE_recruitment_live.xlsx\", read_only=True, data_only=True)
ws = wb[\"f_ty_2_con\"]
h = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
# print specific columns ...
"'
```

The skill should prompt the user for which columns / sheets / row filters
they want to see, OR default to f_ty_2_con + list_rooms summary.

---

## Safety invariants

- **Refuse if auto-cycle is currently running.** Race risk on workbook write.
- **180s timeout.** A normal cycle completes in 60-145s. If it takes longer,
  the timeout kills it cleanly — don't extend.
- **Always `python3 -u`** (unbuffered). Without it, hangs look identical to
  "still running" in the journal/stdout. The 2026-05-13 OOM incident was
  invisible for 21 hours because of buffering — this script avoids that.
- **Don't disable the server-guard hook just to run this.** The hook only
  blocks systemctl stop/disable + rm -rf + reboot — it does NOT block a
  manual export. If you find yourself wanting to disable the hook, you're
  in [[reference-manual-cycle-control]] territory, not this skill.
- **The export writes to the live workbook AND triggers downstream draft
  creation.** A successful trigger means: facility rows materialise into
  `f_ty_2_con`, list_rooms regenerates, then participant draft cycles fire
  on the new state. All those side effects are visible to the maintainer
  team via the shared mailbox + workbook.

## On red (EXIT ≠ 0)

- Don't auto-retry. The next auto-cycle will run in ≤15 min anyway, which
  gives the maintainer time to investigate the FAIL cause first.
- Reference the server-side diagnosis pattern from
  `email_draft_automation/CLAUDE.md` ("Server-side diagnosis" section):

  ```bash
  ssh -i ~/.ssh/ssh-key leitneruser@10.40.41.88 \
    'cd ~/email_draft_automation && set -a && source qualtrics/qualtrics_env.sh \
     && set +a && unset QUALTRICS_WORKBOOK_PATH && \
     QUALTRICS_WORKBOOK_MODE=live QUALTRICS_RUNTIME_STATUS=server \
     timeout 300 .venv/bin/python3 -u qualtrics/export_responses_to_contacts.py \
     > /tmp/export_diag.log 2>&1; \
     echo "EXIT=$?"; tail -30 /tmp/export_diag.log'
  ```

## Composes with

- `/advance-deploy` — typically runs RIGHT BEFORE this skill, to push the
  change being materialised
- `/qualtrics-e2e-pressure-test` — alternative verification path that
  doesn't mutate the live workbook (uses Status=4 personas instead)
