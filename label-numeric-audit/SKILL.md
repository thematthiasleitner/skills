---
name: label-numeric-audit
description: Audit ADVANCE code for NUMERIC assumptions on the label-based Qualtrics CSV (ADR 0003). The export pulls useLabels=True, so CSV fields arrive as TEXT ('Survey Preview', not '1') — any code comparing a CSV field to a numeric code (Status == "1"), or reading the raw export with bare csv.DictReader (bypassing read_csv_from_zip's 3-header-row strip), is a latent bug. Read-only — reports file:line + reason + severity, fixes nothing. Invoke when consolidating CSV reads to the label representation (Workstream B of the standardisation), auditing for dead preview-skip guards, or before relying on any Status/CSV-field comparison. Drives the ADR-0003 "audit every comparison" step.
tools: Bash, Read, Glob, Grep
---

# Label-Numeric Audit Skill

You scan the ADVANCE codebase for the three antipatterns that break under a
**label-based** CSV export (`useLabels=True`), per [ADR 0003]. Read-only.

Why this exists: `Status` (and every choice field) ships as **text**
(`Survey Preview`), not numeric (`1`). Code written against the numeric form is
silently dead — the live example is two preview-skip guards (`Status == "1"`)
that never fire.

---

## When to invoke

- Workstream B of the date/time + label standardisation ("audit every comparison").
- "Does any code assume Status is numeric?" / "Find dead preview guards."
- Before trusting a CSV-field comparison or adding a new CSV reader.

## Workflow

Logic in [_label_numeric_audit.py](_label_numeric_audit.py). Run from inside
`email_draft_automation` (pure code scan — no env, no network):

```bash
cd email_draft_automation
python3 ~/.claude/skills/label-numeric-audit/_label_numeric_audit.py
# widen the net:
python3 ~/.claude/skills/label-numeric-audit/_label_numeric_audit.py --globs 'qualtrics/*.py' 'src/*.py' 'tools/*.py'
```

### Findings, by severity
- **⛔ HIGH** — `status == "<digit>"` / `.get("Status") == "<digit>"` / `int(... Status)`.
  A dead numeric comparison against a text field. Fix: compare the label, or route
  through the one tolerant chokepoint (`normalize_status()` / `is_live_response()`).
- **🔎 REVIEW** — bare `csv.DictReader`. Only a bug **if it reads the Qualtrics
  RESPONSE export** (then it skips `read_csv_from_zip` and ingests 2 phantom
  header rows). Harmless for unrelated local CSVs — open the file and check the
  source before acting.

Lines already routed through the chokepoint (`normalize_status`,
`_STATUS_LABEL_TO_NUM`, `is_live_response`, `is_preview`) are **skipped** — they're
the correct pattern, not a finding.

## Known scope / limits

- Heuristic regex, single-line. It won't trace a value across assignments
  beyond the same line; pair a HIGH hit with `/qualtrics-column-trace` on the
  field if you need the full data flow.
- The REVIEW (DictReader) bucket intentionally over-includes — verify each
  target rather than blanket-fixing.
- As of 2026-06-04 a clean run shows **2 HIGH** (`create_correction_drafts.py:282`,
  `check_avail_mismatches.py:229`) + DictReader REVIEWs. After Workstream B,
  HIGH should be 0.

## Composes with

- `/qualtrics-column-trace` — trace a flagged field end-to-end.
- `/qualtrics-export` — the CSV schema + the "consult CSV and JSON" rule.
- ADR `docs/adr/0003-label-based-csv-consumption.md` — the governing decision.
