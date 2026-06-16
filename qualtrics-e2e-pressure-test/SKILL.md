---
name: qualtrics-e2e-pressure-test
description: Submit a test persona to the live ADVANCE Qualtrics survey, pull the resulting CSV, feed it through the production export pipeline locally, verify expected workbook column values + course_ids, then cleanly delete the response. **High-risk (writes Status=4 test responses to live Qualtrics) — DO propose via AskUserQuestion when relevant, but NEVER silently invoke. Explicit user consent required.** Typically follows /qualtrics-restructure-step + --apply, to verify the change end-to-end against real Qualtrics + the production code path. Surface this skill whenever the user has just modified the survey and wants to verify it works, OR mentions wanting to pressure-test / end-to-end-test a Qualtrics change. Catches CSV-shape surprises, dispatch routing bugs, and Phase 1 sentinel-override issues before they reach real facility submissions.
tools: Bash, Read, Write, Edit, Glob, Grep
---

# Qualtrics End-to-End Pressure Test Skill

You orchestrate a complete round-trip verification of a survey change against the
live ADVANCE Qualtrics survey + production export pipeline. This is the pressure-test
discipline distilled from Phase 4 iterations 1, 5, 6 — each of which used the same
6-step verification pattern.

**This skill writes to live Qualtrics (Status=4 Imported test responses) — high-risk.**

**Discovery vs invocation pattern** (per project CLAUDE.md "Skill-suggestion checkpoint"):

- ✅ **DO surface this skill via `AskUserQuestion`** whenever the user is in a
  context where it would help (just shipped a survey change, asks about
  pressure-testing, wants to verify a change end-to-end).
- ❌ **NEVER silently invoke** without explicit consent. The risk of writing
  test data to a shared survey is too high for "I'll just run it and report".
- ✅ **If the user types `/qualtrics-e2e-pressure-test`**, that IS explicit
  consent — proceed directly.

The AskUserQuestion proposal should:
- Name the skill + what it will do ("submit 1-2 Status=4 test responses,
  pull the CSV, verify pipeline, then DELETE the responses")
- Estimate side effects ("~3 min, creates 2 Qualtrics responses temporarily
  marked Imported, deletes them on completion")
- Offer at least one alternative ("alternatively: skip the live test and
  rely on Layer C structural checks only")

**Composability:** runs after `/qualtrics-restructure-step` + manual `--apply`.
Composes with `/qualtrics-csv-pull` (which extracts the CSV-fetch substep).

---

## When to propose (then await explicit consent)

User has just applied a survey change to live Qualtrics and wants to verify it
works end-to-end. The typical sequence is:

1. Build a restructure script (via `/qualtrics-restructure-step` or manually)
2. Dry-run → review → `--apply`
3. **Propose `/qualtrics-e2e-pressure-test` via AskUserQuestion** ← you are here
4. On user consent (either approval of the question OR explicit `/<name>` typing):
   run the workflow

If the user typed `/qualtrics-e2e-pressure-test` themselves, skip step 3 and
go straight to step 4 — that's explicit consent.

## When NOT to propose

- For survey changes that haven't been `--apply`ed yet — there's nothing live
  to test. Propose `/qualtrics-restructure-step` first if appropriate.
- For code-only changes (no Qualtrics mutation) — propose `make test-a` instead.
- For workbook-only inspection — propose `/advance-server-cycle-trigger` +
  workbook read instead.

## When to invoke directly (no AskUserQuestion needed)

- The user typed `/qualtrics-e2e-pressure-test` in the chat — explicit consent
- The user already approved a multi-step plan that included this skill — implicit consent from the plan approval

---

## Workflow

### Step 0: Confirm + select persona

Ask the user:
- Which persona to submit? (path or stem under `tests/personas/responses/`)
- If no persona exists for the change, scaffold one based on the change's intent.
  Use F01/F08/F09 (in tests/personas/responses/) as templates.

For NEW personas: ALWAYS use `*@advance-test.invalid` email pattern (the project
invariant for marking test data) and `status: 1` in the values dict.

### Step 1: Validate the persona payload

```bash
cd email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a
.venv/bin/python3 tools/submit_persona_responses.py --validate --only <stem>
```

Stop here if validation fails — fix the persona JSON before submitting.

### Step 2: Submit to live Qualtrics (Status=1 → Qualtrics stores as Status=4 Imported)

```bash
.venv/bin/python3 tools/submit_persona_responses.py --only <stem>
```

Capture the returned ResponseId — needed for cleanup.

### Step 3: Pull the live CSV via export-responses

Use [_e2e_helper.py](_e2e_helper.py) (in this skill folder) which handles:
- The 3-step async export endpoint (start → poll → download → unzip → parse)
- The 5-15s indexing lag (retries once with a wait)
- The CSV-column-name dual-key lookup (`f_ty_2_contact_email` AND `QID7_TEXT` —
  this is the bug I hit in iter 6, the helper avoids it for you)

### Step 4: Feed rows through production pipeline

```python
from email_draft_automation.qualtrics.export_responses_to_contacts import (
    build_f_ty2_rows_from_response, compute_list_rooms_rows,
    F_TY2_HEADER, LIST_ROOMS_HEADER,
)
from email_draft_automation.qualtrics.course_id_registry import CourseIdRegistry
import tempfile
with tempfile.TemporaryDirectory() as td:
    reg = CourseIdRegistry(Path(td) / 'assignments.json')
    f_ty2_rows = build_f_ty2_rows_from_response(csv_row, F_TY2_HEADER)
    list_rooms = compute_list_rooms_rows(
        f_ty2_rows=f_ty2_rows,
        f_tor2_rows=[], f_tor3_rows=[], participant_rows=[],
        existing_header=LIST_ROOMS_HEADER, course_id_registry=reg,
    )
```

### Step 5: Print structured assertions

For each persona:
- CSV columns the change targeted: present? values correct?
- f_ty_2_con post-dispatch: target fields populated as expected?
- list_rooms: course_id format matches the regex? (e.g. `^GE_\d{4}-\d{2}-\d{2}_\w+_\d{2}$`
  for physical, `^ZOOM_...` for online)
- For Zoom personas: `is_online == "TRUE"`, sentinel canton/city/addr present
- For Physical personas: `is_online == ""` (empty string, not None)

Use clear ✓/✗ output.

### Step 6: Cleanup (always, even on assertion failure)

```python
state_path = 'tests/personas/.last_submission.json'
state = json.load(open(state_path))
rid = state['<PersonaId>']
requests.delete(
    f'{base}/surveys/SV_aWrEE8bXIdc6Pqe/responses/{rid}',
    headers={'X-API-TOKEN': token}, timeout=30,
)
del state['<PersonaId>']
json.dump(state, open(state_path, 'w'), indent=2, sort_keys=True)
```

Then re-pull the CSV to confirm the response is absent.

---

## Safety invariants

- **Persona email must end in `@advance-test.invalid`.** This is now the SOLE
  thing keeping personas out of live: the live export drops any row whose email
  is in that marker domain (or a trai_onl trainer-name marker), independently of
  status — `response_enters_live` / the live-only `exclude_test_markers` gate
  (deploy-2026-06-09). A wrong/real email here WOULD create real recruitment
  data now that the status gate is relaxed. Mistakes here are higher-stakes than
  before — double-check the email.
- **Status=1 in persona JSON, Qualtrics stores as Status=4 Imported.** As of the
  Status=4 gate (2026-06-09) the LIVE workbook now ADMITS Status=4 (gate `0,4`),
  so status no longer excludes personas — the **test-marker email** does. Real
  (non-marker) Status=4 imports DO enter live by design (that's how
  `tools/inject_facilitator_response.py` binds facilitators). The pressure test
  still verifies via local pipeline + raw CSV; a marker persona must NOT appear
  in the live workbook (Layer C `no-test-marker-in-live` enforces this).
- **Cleanup runs always.** Wrap the assertions in try/finally — if a Pipeline
  assertion fails, you still DELETE the response. Leaving Status=4 imports
  hanging around forever pollutes future re-tests.
- **Don't submit if zoom.team_meeting_url is unset AND the persona tests a Zoom
  flow.** Check first; warn the user. The skipped-draft would mask a real failure.

## Common pitfalls (lessons from this session)

- **CSV column-name lookup**: the CSV header row 1 uses DataExportTag
  (`f_ty_2_contact_email`), NOT QID-suffixed (`QID7_TEXT`). Always lookup with
  `d.get('f_ty_2_contact_email') or d.get('QID7_TEXT') or ''`. The helper does this.
- **Export-responses indexing lag**: a fresh ResponseId may not appear in the
  CSV for 5-15s. If the first pull doesn't find it, wait 15s and retry once
  before declaring missing.
- **Synthetic slot data may be needed**: if testing a Physical-only change
  but the facility data needs slots to produce a list_rooms row, augment the
  CSV row dict with synthetic slot keys before feeding to `compute_list_rooms_rows`.
  This is honest (CSV shape comes from real Qualtrics, slot vals are synthetic
  for scope of change).
- **Zoom override fires inside `compute_list_rooms_rows`, NOT in
  `build_f_ty2_rows_from_response`.** A Zoom persona without slot data → empty
  list_rooms output, so the override never fires. Add synthetic slot or check
  earlier in the pipeline.

## Composes with

- `/qualtrics-restructure-step` — produces the survey change you're verifying
- `/qualtrics-csv-pull` — used internally for step 3
- `/qualtrics-export` — reference for CSV column-name conventions
