---
name: workbook-format-census
description: Census date/time/number format shapes across every sheet of an ADVANCE recruitment workbook, flag the format-MIXED columns, and split the two families — Family A (course/event dates+times humans read & emails render → should be one canonical dd/mm/yyyy + HH:MM) vs Family B (machine ISO audit stamps like *_at / *_sent_at / recorded_date → leave alone). Read-only. Invoke as the before/after verification for any date/time standardisation, to find inconsistently-formatted course dates/times, or to confirm a normalisation landed without touching the ISO stamps. Reproduces the census that drove the 2026-06-04 decision (canonical = slash, the existing 90% majority).
tools: Bash, Read, Glob, Grep
---

# Workbook Format Census Skill

You scan a workbook and report, per sheet, the **format shapes** of every
date/time column — and flag which are MIXED. Read-only.

The purpose: decide and verify date/time standardisation. It separates the two
families so you never "normalise" a machine timestamp or a duration by mistake:

- **Family A** — course/event dates & times (`f_ty_room_tn_begin(n)`, `_time`,
  `part_prog_start_date`/`_time`, `course_start_date`/`_time`, `session_date`,
  `admin_rec_date`, training dates). Humans read these; emails render them.
  These SHOULD share one canonical: **`dd/mm/yyyy` + `HH:MM`** (the slash form
  is ~90 % of the workbook + what emails already render).
- **Family B** — machine audit stamps (`*_at`, `*_sent_at`, `*_logged_at`,
  `*_draft_at`, `recorded_date`, `*_fini_date`). ISO on purpose; drive dedup
  (`first_outreach_sent_at`) and sorting. **LEAVE ALONE.**

Duration-like columns (`*_hours`, `*_weeks`, `room_hours_remain`, `_cap`) are
NUMBERS, not clock times — excluded from the time census so they're never
mis-normalised.

---

## When to invoke

- "Census the workbook's date/time formats." / "Which columns are format-mixed?"
- Before a standardisation: see the spread + pick the canonical.
- After a standardisation: confirm Family A is now uniform and Family B untouched.

## Workflow

Logic in [_format_census.py](_format_census.py). Run from inside
`email_draft_automation` (no env needed — pure workbook read):

```bash
cd email_draft_automation
# Live workbook, MIXED-focus (default):
python3 ~/.claude/skills/workbook-format-census/_format_census.py

# Preview workbook (for snapshot/diff testing):
python3 ~/.claude/skills/workbook-format-census/_format_census.py --workbook Qualtrics_ADVANCE_recruitment_preview.xlsx

# Show ALL date/time columns, not just MIXED (to see the canonical they agree on):
python3 ~/.claude/skills/workbook-format-census/_format_census.py --all-shapes

# Only one family:
python3 ~/.claude/skills/workbook-format-census/_format_census.py --family A
```

Output: per sheet, `[A|B] <column> {shape: count}` with `<== MIXED` on
multi-shape columns, then a `Family-A columns that are format-MIXED: N` tally —
the **acceptance metric** for the standardisation (target: 0).

Shapes: `D:d/m/Y`, `D:d.m.Y`, `D:ISO`, `D:d-m-Y` (dates); `T:H:MM`, `T:H.MM`,
`T:Hh`, `T:bareH` (times).

## Safety invariants

- **Read-only** — never writes the workbook.
- **Never normalise Family B or duration columns** — the census deliberately
  classifies them so a downstream fix skips them. ISO stamps drive dedup/sort;
  changing them breaks `first_outreach_sent_at` + `sent_log` ordering.
- The classifier is **heuristic** (regex on column names + value shapes). Eyeball
  a surprising classification before acting; extend `FAMILY_B`/`DURATION` if a
  new column is mis-bucketed.

## Composes with

- `/qualtrics-column-trace` — drill into ONE mixed column (where it comes from,
  why it's mixed).
- `tools/snapshot_workbook.py` + `tools/workbook_diff.py` — the before/after
  cell-diff; this skill is the before/after *format* view.
