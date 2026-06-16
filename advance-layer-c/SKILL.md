---
name: advance-layer-c
description: Manually run the ADVANCE nightly Layer C drift detector on the production server, on demand — typically at the END of a coding session to confirm nothing regressed before you log off. SSHs to leitneruser@10.40.41.88 and runs the exact nightly entry point (run/run_layer_c_smoke.sh → tools/layer_c_smoke.py) against the LIVE workbook + live Qualtrics survey + calendar dry-run, then prints the per-check PASS/FAIL/SKIP table and overall verdict. Read-only (no mutations) but the agent-lock guard may still fail-closed-block the SSH from an OneDrive-rooted session — claim the lock if blocked. Runs the wrapper DIRECTLY (not via the systemd nightly service), so it does NOT post to the #advance-server-log Slack channel (confirmed 2026-06-15) — that channel is for the automated 00:00 run only. Use when the user wants to "run the midnight/Layer C test now", "check the nightly drift detector", or verify live health after a deploy. Composes with request-ssh-access (server reachability), advance-cycle-status (deploy/cycle health), advance-promote (verify a tag landed).
---

# advance-layer-c

Runs the **same Layer C drift detector that fires nightly at 00:00** on the
server, but on demand. Layer C is the upstream-drift detector (live Qualtrics
survey definition + context_packs + workbook headers + dispatch tags +
recruitment validations/todos + facility-signout + questionnaire-links +
calendar dry-run, etc.). Nightly results land in Slack **#advance-server-log**;
this skill lets you get the same verdict at the end of a session without
waiting for midnight.

**Read-only** — no workbook writes, no drafts, no deploy. Logically it needs no
lock, **but in practice the agent-lock PreToolUse guard may fail-closed-block the
server SSH** (it pattern-matches `systemctl`/`git`/`journalctl`/server paths and is
conservative — confirmed blocking a read-only server read 2026-06-15 from an
OneDrive-rooted session; cf. `reference_agent_lock_identity_split`). If you get
`BLOCKED by agent-lock`, just claim it first (default identity, NOT a custom
`ADVANCE_AGENT_ID`) and release when done:
```bash
python3 tools/agent_lock.py claim "layer-c live run"   # separate Bash call from the ssh
# … run the Layer C command below …
python3 tools/agent_lock.py release
```
Claiming is safe and non-exclusive here (the run only reads).

## Preconditions

- **UNIGE VPN connected** — the server (`10.40.41.88`) is only reachable on the
  university network. A connection timeout means the VPN is down, not that the
  server is dead.
- **SSH key loaded** (`~/.ssh/ssh-key`). If `ssh-add -l` shows no identity, run
  **`/request-ssh-access`** first (you load it in your own terminal; the
  passphrase never enters the conversation).

## Run it (read-only, does NOT post to Slack)

```bash
ssh -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 \
  'bash ~/email_draft_automation/run/run_layer_c_smoke.sh; echo "EXIT=$?"'
```

The wrapper sources `qualtrics/qualtrics_env.sh` (the survey + questionnaire-link
checks need the Qualtrics API token), `cd`s into the repo, and runs
`tools/layer_c_smoke.py`. It exits non-zero if any check FAILs, so `EXIT=0`
means a fully green run.

Faster, slow checks skipped (calendar-dry-run, context-packs):

```bash
ssh -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 \
  'bash ~/email_draft_automation/run/run_layer_c_smoke.sh --quick; echo "EXIT=$?"'
```

Skip a specific noisy check (substring match), e.g. while a known issue is open:

```bash
ssh -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 \
  'bash ~/email_draft_automation/run/run_layer_c_smoke.sh --skip questionnaire-links; echo "EXIT=$?"'
```

## Why this does NOT spam #advance-server-log

The nightly Slack post is wired into the **systemd nightly service environment**
(the `email-drafts` timer at 00:00), not into `layer_c_smoke.py` / the wrapper
itself. Invoking the wrapper directly over SSH runs the checks and prints to
stdout only — no webhook fires. **Confirmed 2026-06-15:** a manual run left
#advance-server-log untouched (the latest message stayed the 00:05 nightly). If a
future change moves the webhook into the script (gated on e.g. a
`SLACK_WEBHOOK_URL` env var), run with that var unset:
`env -u SLACK_WEBHOOK_URL bash ~/email_draft_automation/run/run_layer_c_smoke.sh`.

## Interpreting

The script prints one line per check — `PASS` / `FAIL` / `SKIP` — and a tail
summary like `19 PASS, 2 FAIL, 0 SKIP`.

- **`EXIT=0`, all PASS** → live state is clean; safe to log off.
- **Any `FAIL`** → Layer C is a *drift detector*, not a local gate. A red check
  means something changed **live** (Qualtrics survey edited, mailbox/token
  state, a signed-out facility, an unshared survey). **Diagnose root cause
  before re-capturing or skipping** — never silence a check to make it green.
  - `facility-signout-hidden` → a `list_rooms` course is sourced from a
    signed-out `f_ty_2_con` room. Note the per-slot granularity: a multi-room
    facility response (one ResponseId, several rooms) can have just one room
    signed out; the check must match on (ResponseId + slot), not ResponseId
    alone.
  - `questionnaire-links-accessible` → a survey in
    `context/config/questionnaire_links.json` isn't readable by the automation
    API token; the survey owner must share it with View-Reports rights
    (recurs for post/fup_2/fup_6 — see
    `reference_qualtrics_cross_account_survey_sharing`).
  - `calendar-dry-run` failing with `MissingGraphToken` → Graph auth is down;
    use `advance-graph-health`.
- **`SKIP`** → a check couldn't run its precondition (e.g. workbook path
  unresolved). The first nightly choice-registry run is an expected baseline
  SKIP.

## Composes with

- **request-ssh-access** — satisfy the SSH precondition.
- **advance-cycle-status** — deploy tag + 15-min cycle health (this skill is
  the deeper live-invariant pass).
- **advance-graph-health** — when `calendar-dry-run` fails on the Graph token.
- **advance-promote** — run this right after a deploy to confirm the change is
  live and didn't break an invariant.

## Test

None — the verdict depends on the live server, live Qualtrics survey, and live
workbook; a mocked runner would assert nothing real (same rationale as
`advance-cycle-status` / `advance-graph-health`). Correctness of the underlying
checks is covered by `tools/layer_c_smoke.py` running nightly + the hermetic
unit tests for individual invariants under `tests/`.

## History

Built 2026-06-15 after three consecutive nightly Layer C FAILs
(`facility-signout-hidden` false-positive on a per-slot Zoom sign-out;
`questionnaire-links-accessible` cross-account sharing) showed the team needed
an on-demand, end-of-session way to run the midnight drift detector without
waiting for 00:00 or spamming #advance-server-log.
