---
name: qualtrics-inject-row
description: Inject a REAL facilitator availability (f_tor_3) binding into the live ADVANCE survey as a Status=4 response via the responses API — the durable, auditable replacement for hand-edited manual_entry workbook rows. Wraps email_draft_automation/tools/inject_facilitator_response.py. HIGH-RISK (writes a live row that enters the live workbook on the next cycle) — propose via AskUserQuestion, never silently invoke; explicit consent required. Use when a NEW facilitator needs binding to a course that is still soliciting a facilitator (a current QID23 choice). NOT usable to swap an already-bound course (it has left the dropdown — see the constraint).
---

# qualtrics-inject-row

Create a facilitator→course binding as a genuine Qualtrics **Status=4 (Imported)**
response instead of editing `manual_entry` rows into the workbook. Background: the
live export now admits Status=4 minus test-marker emails (the Status=4 gate,
deploy-2026-06-09), so a real import binds normally via
`find_tor_info(f_tor_3_avail_1 == course_id)` on the next cycle. No workbook
surgery, no rclone-bisync clobber risk.

**This writes to live Qualtrics — high-risk.** Propose via `AskUserQuestion` (per
project CLAUDE.md skill-suggestion checkpoint); proceed only on explicit consent
or the user typing `/qualtrics-inject-row`.

## Hard constraint (proven 2026-06-09)

The availability question `QID23` (`f_tor_3_avail_1`) import value must be a
**numeric choice key**, and the survey only offers choices for courses currently
**soliciting** a facilitator (`f_tor_3_avail-online=true`). A course already bound
has LEFT the dropdown and has no key — it **cannot** be injected without first
un-binding it (which opens a ~1-cycle facilitator-less gap, dropping it from
`part_avail`). The dropdown also renumbers each cycle, so resolve the key fresh.
The tool refuses a course that isn't a current choice and explains the trade-off.

## Workflow

```bash
cd <clone>/email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a

# 1. see which courses are currently bindable (still soliciting a facilitator):
.venv/bin/python3 tools/inject_facilitator_response.py --list-choices

# 2. rehearse on the marker domain (safe — excluded from live):
.venv/bin/python3 tools/inject_facilitator_response.py \
    --first Julie --last "Da Silva" --email juliedasilva25@gmail.com \
    --interven COG --lang FR --course-id <ZOOM_...> --test --apply
#    -> verify it round-trips, then DELETE it:
.venv/bin/python3 tools/inject_facilitator_response.py --delete R_xxx --apply

# 3. for real (real email; enters live next cycle):
.venv/bin/python3 tools/inject_facilitator_response.py \
    --first ... --last ... --email <real> --interven ... --lang ... \
    --course-id <ZOOM_...> --apply
```

Interventions: `COG | SH+ | POD | "SH+ & COG"`. Lang: `FR | DE`.

## Verify + safety

- After the next ~15-min cycle, confirm the binding with `/advance-cycle-status`
  (lock-gated workbook read) or `tools/layer_c_smoke.py` (`part-avail-courses-online`).
- Claim the **agent-lock** before any live injection (shared Qualtrics surface).
- `--test` forces `@advance-test.invalid` (Layer C `no-test-marker-in-live` keeps
  it out of live); always `--delete` test rows afterwards.
- Status=4 + a real email = a real live row. Triple-check the email + course_id.

## Composes with

- `/qualtrics-survey-pull` — inspect QID23 choices / recodes directly
- `/advance-cycle-status` — confirm the binding materialised live
- `/qualtrics-e2e-pressure-test` — the marker-based test path (personas)
