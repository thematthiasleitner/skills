---
name: qualtrics-restructure-step
description: Scaffold an idempotent, --dry-run-default Python script that mutates the ADVANCE Qualtrics survey (add/edit/rename/delete a question, add display logic, change validation, restructure a block). Invoke when the user wants to make a step-by-step survey change as part of an iterative restructure (e.g. any Phase 4 iteration of docs/facility_address_first_plan.md), or whenever they ask to "add a new question", "change validation", "add display logic", "rename a tag", or "restructure a block" in Qualtrics survey SV_aWrEE8bXIdc6Pqe.
tools: Bash, Read, Write, Edit, Glob, Grep
---

# Qualtrics Restructure Step Skill

You scaffold ADVANCE-project survey-mutation scripts that follow a consistent
pressure-tested pattern: idempotent, dry-run-default, atomic-API-call, pretty-print.

**Composability:** complements `/qualtrics` (REST API patterns) and `/qualtrics-export`
(CSV format). After invoking this skill, the user typically runs `/qualtrics-e2e-pressure-test`
to verify the change end-to-end.

---

## When to invoke

User wants to make ONE focused change to the ADVANCE Qualtrics survey
(`SV_aWrEE8bXIdc6Pqe`):

- Add a new question to a block
- Add display logic to one or more existing questions
- Change validation rules (ForceResponse, ValidNumber, etc.)
- Rename a DataExportTag
- Restructure block flow (reorder, remove from BlockElements, add a page break)
- Add or modify Choices on an MC question

If the change is more than ONE focused mutation, propose breaking it into iterations
first. The whole value of this skill is small surgical scripts.

## When NOT to invoke

- User wants to read survey state (use `/qualtrics-csv-pull` or direct `/qualtrics` API)
- User wants to verify a change end-to-end (use `/qualtrics-e2e-pressure-test`)
- User wants help understanding what the CSV looks like (use `/qualtrics-export`)
- The change spans multiple unrelated blocks/questions (propose breaking into multiple
  skill invocations, one per logical change)

---

## Workflow

1. **Ask the user the 5 setup questions** (or infer from their phrasing):
   - **Iteration number + short name**: e.g. `step_8_add_capacity_validation`
   - **Mutation type**: ADD_QUESTION | EDIT_QUESTION | RENAME_TAG | DISPLAY_LOGIC | BLOCK_REORDER | VALIDATION_CHANGE
   - **Target block ID** (if relevant): e.g. `BL_0uh9Py9rkP3a6Ls`
   - **Target QID(s)** (for EDIT/RENAME/DISPLAY_LOGIC): e.g. `QID265`
   - **Idempotency probe**: how do we know this mutation is already applied?
     (typically: a DataExportTag exists, or a Validation.Settings field has the target value)

2. **Read [PATTERN.md](PATTERN.md)** in this skill folder to refresh the canonical
   patterns from the 7 reference scripts already in the codebase.

3. **Read the closest existing script** as a template — match it by mutation type:
   - ADD_QUESTION → `tools/restructure_facility_step_1_add_kind.py`
     (one question) or `tools/restructure_facility_step_5a_add_slots.py` (many)
   - EDIT_QUESTION → `tools/restructure_facility_step_7_tighten_slot_force.py`
   - RENAME_TAG → `tools/restructure_facility_step_2_rename_tags.py`
   - DISPLAY_LOGIC → `tools/restructure_facility_step_6_zoom_display_logic.py`
     (single condition) or `tools/restructure_facility_step_5c_slot_count_gating.py`
     (OR of multiple conditions)
   - BLOCK_REORDER → `tools/restructure_facility_step_5b_remove_legacy_slots.py`

4. **Generate the new script** at
   `email_draft_automation/tools/restructure_facility_<iter_name>.py`,
   using [_skeleton.py](_skeleton.py) as a starting point and filling in the
   action-specific helpers.

5. **Validate**:
   - `.venv/bin/python3 -c "import ast; ast.parse(open('<path>').read())"` — syntax check
   - `.venv/bin/python3 tools/<script>.py --help` — argparse loads
   - `.venv/bin/python3 tools/<script>.py` (dry-run, default) — runs against live
     Qualtrics WITHOUT mutating, prints planned changes

6. **DO NOT run `--apply`**. Stop there. Hand back to the user with:
   - Path to the generated script
   - Dry-run output
   - The explicit warning: "next step is `--apply` which writes to live Qualtrics —
     you decide when"

   This skill never mutates live state itself. It only scaffolds + dry-runs.

---

## Mandatory structure of the generated script

The skeleton enforces these 9 sections. Do not deviate:

1. **Module docstring**: `Phase X iter Y: <one-line intent>` + Plan reference
2. **Imports**: argparse, json, os, re, sys, requests, Path, Optional
3. **Constants**: BASE_DIR, ENV_PATH, SURVEY_ID, target block/QIDs
4. **`_load_env()`**: source qualtrics_env.sh
5. **`_env(name)`**: typed env-var reader
6. **Action-specific helpers**: build_payload / build_display_logic /
   find_existing / etc. (the only section that varies meaningfully across scripts)
7. **API helpers**: get_*, put_*, post_* (copy from skeleton)
8. **`main(argv)`**: argparse → print header → idempotency probe → planning →
   if --dry-run: summary + return → if --apply: per-op loop with failure tracking →
   final summary
9. **`if __name__ == "__main__": sys.exit(main())`**

---

## Safety invariants

- **Default mode is --dry-run.** The script must run without arguments and print
  what it WOULD do, never mutating.
- **Per-op failure tracking.** When applying, each API call's success/failure is
  recorded and printed in the summary. Partial failures must not abort silently.
- **Idempotency probe.** Re-running the script (or running it after partial failure)
  must skip already-applied changes. Probe by tag presence, validation field value,
  or DisplayLogic JSON content — depending on the mutation type.
- **No bulk writes.** Each question gets its own GET → patch → PUT (atomic at the
  question level). If the script needs to update a block, the block PUT happens
  AFTER all question PUTs succeed, in the same script run.
- **Stick to per-question PUT for mutations.** Bulk PUT to /survey-definitions
  is supported by Qualtrics but harder to recover from on partial failure.

## Composes with

- `/qualtrics` — for Qualtrics REST API endpoint reference
- `/qualtrics-export` — for CSV column-name reference
- `/qualtrics-e2e-pressure-test` — to verify the change end-to-end after --apply
- `/advance-deploy` — to commit + push + Layer C verify after the change is live
