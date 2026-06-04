---
name: qualtrics-column-trace
description: Trace one ADVANCE column end-to-end across all four layers — survey question (alive? orphaned? what format does it enforce?) → CSV DataExportTag (which columns carry it, value distribution) → export code (every file:line that references it) → workbook (which sheets hold it, value/format distribution, MIXED flag). Read-only. This is the investigative loop the f_ty_2_con audit and the dead-column audit both hand-rolled. Invoke when you need to answer "where does this column come from, is its source still alive, and what's actually in it?" — diagnosing a blank/stale column, deciding whether a column is dead, checking a column's format consistency, or understanding how a workbook column maps back to the survey. Composes /qualtrics-survey-pull + /qualtrics-csv-pull + code grep + an openpyxl scan.
tools: Bash, Read, Glob, Grep
---

# Qualtrics Column Trace Skill

You trace a single column across the whole ADVANCE pipeline and produce a
four-layer report. Read-only — pulls and scans, never mutates.

This skill exists because column work **cannot** be reasoned about from code
alone (per ADR 0003 / the `/qualtrics-export` "consult CSV **and** JSON" rule):
you must check whether the source question still exists on Qualtrics (JSON),
whether its data still arrives (CSV), how the code maps it, and what's actually
persisted (workbook). This runs all four at once.

---

## When to invoke

- "Where does `f_ty_room_tn_begin(n)` come from and why is it format-mixed?"
- "Is `part_zoom` dead? Its column is blank for new rows."
- "Trace `admin_rec_date` — which sheets, which formats?"
- Any column audit, dead-column scan, or "is this still wired up?" question.

## When NOT to invoke

- To pull *only* the CSV or *only* the survey JSON → use `/qualtrics-csv-pull`
  or `/qualtrics-survey-pull` directly.
- To **change** a column / question → `/qualtrics-restructure-step`.

---

## Workflow

Logic lives in [_column_trace.py](_column_trace.py). Run from inside
`email_draft_automation` with env sourced (only needed if it has to pull fresh):

```bash
cd email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a

# Trace using the newest saved CSV + survey JSON in qualtrics/ (fast):
python3 ~/.claude/skills/qualtrics-column-trace/_column_trace.py 'f_ty_room_tn_begin(n)'

# Force fresh survey + CSV pulls (when nothing saved this session, or to be current):
python3 ~/.claude/skills/qualtrics-column-trace/_column_trace.py part_zoom --pull
```

Accepts EITHER a workbook column (`f_ty_room_tn_begin(n)`) OR a CSV
DataExportTag (`part_zoom`, `f_ty_addr_slot_1_start_date`). It normalises a
`_core` (strips leading `N_`/`<digit>_`, trailing `(n)`, `_tN_` loop infixes)
so loop/parenthetical variants match.

### The four sections it prints
1. **SURVEY** — QID, type, validation/date-format, block (or `<NO BLOCK → dead>`), in_flow.
2. **CSV** — matching columns + per-column value distribution (top values).
3. **CODE** — every `file:line` in `qualtrics/*.py` + `src/*.py` that names the column.
4. **WORKBOOK** — each sheet holding it + non-empty count + format-shape distribution (flags `MIXED`).

---

## Reading the output / known limitation

- `<NO BLOCK — orphaned/dead>` in section 1 is the decisive **dead-source**
  signal (e.g. the legacy `f_ty_room_N_tM_*` questions).
- **Cross-tag mappings won't auto-link in the CSV section.** When a workbook
  column is *derived* from a differently-named CSV tag (e.g. workbook
  `f_ty_room_tn_begin(n)` is fed by CSV `f_ty_addr_slot_1_start_date`), the
  `_core` differs so section 2 shows "no match" — but **section 3 (CODE)
  reveals the bridge** (look for `"start_date": "f_ty_room_tn_begin(n)"`). Read
  the CODE section to find the real CSV source, then trace that tag too.
- Artifacts are **reused if present** (newest dated file in `qualtrics/`), so a
  trace right after a pull is instant. Pass `--pull` to force current data.

## Safety invariants

- **Read-only.** No Qualtrics mutation, no workbook write. Defaults to the LIVE
  workbook for reads only; pass `--workbook …_preview.xlsx` to inspect preview.
- **Label CSV only** — relies on the `useLabels=True` export (per ADR 0003).

## Composes with

- `/qualtrics-survey-pull` + `/qualtrics-csv-pull` — used internally; run them
  standalone if you only need one layer.
- `/workbook-format-census` — when you want the format picture for ALL columns
  at once, not one.
- `/qualtrics-export` — CSV schema + the consult-CSV-and-JSON rule this enforces.
