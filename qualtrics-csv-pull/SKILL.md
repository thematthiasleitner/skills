---
name: qualtrics-csv-pull
description: Pull the live ADVANCE Qualtrics CSV via the 3-step async export endpoint (start → poll → download → unzip → parse) with useLabels=True, and return a list of dicts keyed by both DataExportTag column names AND QID-based ImportId. Read-only — no Qualtrics state is mutated. Invoke when any task needs to read live Qualtrics respondent data without going through the full export_responses_to_contacts pipeline (debugging a specific response, verifying a column's value after a survey change, sanity-checking what's actually in the CSV after a question rename, comparing CSV state before/after a mutation). The 30-line CSV-pull incantation that was re-written inline 4× during Phase 4 of facility_address_first_plan.md.
tools: Bash, Read, Glob, Grep
---

# Qualtrics CSV Pull Skill

You pull the live ADVANCE Qualtrics survey responses as a CSV, parse them
into Python dicts, and return them in a shape that's easy to query.

**Read-only.** No Qualtrics mutations. Safe to invoke whenever live respondent
data is needed.

**Composability:** complements `/qualtrics` (REST API reference) and
`/qualtrics-export` (CSV format details). Used internally by
`/qualtrics-e2e-pressure-test` (you don't need to invoke this separately if
you're already running that skill).

---

## When to invoke

Auto-triggers naturally when the user asks anything like:
- "What's the CSV value for X column in Y response?"
- "Did the survey rename go through? Show me the new column."
- "Pull the live responses and show me anything matching..."
- "How many facility responses are there?"
- "Inspect Qualtrics for ResponseId R_xxx"

## When NOT to invoke

- For workbook (Excel) inspection — use direct `openpyxl.load_workbook(...)`
  on `Qualtrics_ADVANCE_recruitment_live.xlsx` or `_preview.xlsx`.
- For Qualtrics SURVEY DEFINITION (questions, blocks, flow) — use
  `GET /survey-definitions/SV_aWrEE8bXIdc6Pqe` directly (the `/qualtrics` skill
  has the pattern).
- For full pipeline materialisation — use `/qualtrics-e2e-pressure-test`.

---

## Workflow

### Default: invoke the helper

The CSV-pull logic lives in [_csv_pull.py](_csv_pull.py) (in this skill folder).
It handles:
- The 3-step async endpoint (`POST /export-responses` → poll progressId →
  GET file)
- 5-15s indexing lag retry (optional, via `--retry-on-missing` flag)
- Dual-key dict construction so callers using EITHER `'f_ty_2_contact_email'`
  OR `'QID7_TEXT'` get the same value (catches the iter 6 bug)

Two usage modes:

**A. As a CLI** for ad-hoc inspection:
```bash
cd email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a
.venv/bin/python3 ~/.claude/skills/qualtrics-csv-pull/_csv_pull.py \
    --email-substring "f08@" --columns "1_f_ty_addr_kind,1_f_ty_room_canton"
```

**B. As a Python import** in scripts or inline pipelines:
```python
import sys; sys.path.insert(0, str(Path.home() / '.claude/skills/qualtrics-csv-pull'))
from _csv_pull import pull_live_csv, find_rows_by_email_substring

rows = pull_live_csv(retry_on_missing="f08@")
matched = find_rows_by_email_substring(rows, "f08@", "f09@")
print(matched["f08@"]["1_f_ty_addr_kind"])
```

### Output format

The helper returns `list[dict[str, str]]`. Each dict represents one CSV row.
Keys include BOTH:
- `f_ty_2_contact_email` (DataExportTag from header row 1)
- `QID7_TEXT` (synthesized from ImportId metadata in header row 3)

So callers using either lookup pattern work. The QID-key fallback was the
exact bug pattern I hit in iter 6 of the facility restructure.

---

## Safety invariants

- **Always `useLabels=True`** ([[feedback-qualtrics-csv-labels]]). Recode
  values are unreliable. The helper hardcodes this — don't override.
- **Don't bypass the retry mechanism** for freshly-submitted responses.
  Qualtrics has 5-15s indexing lag; the helper handles this with one retry
  + 15s wait. If a row is still missing after that, it's truly absent
  (probably the submission failed silently).
- **Don't cache the result across cycles.** The 15-min export cycle
  rebuilds workbook state; CSV pulls between cycles are snapshots that
  may be slightly stale by the time you act on them.
- **Respect Qualtrics' rate limits.** Don't poll the export endpoint
  more than every 2 seconds (the helper sleeps 2s between polls).

## Common gotchas (from session experience)

- **CSV column for the facility contact email is `f_ty_2_contact_email`**
  (DataExportTag), NOT `QID7_TEXT`. The dual-key fallback the helper
  provides hides this so you don't have to remember which.
- **Status=4 responses (Imported via API) ARE in the CSV** by default.
  The export endpoint doesn't filter by Status unless you pass
  `{"includeIneligibleResponses": True}` (and even then the semantics
  differ from what you'd guess).
- **Empty cells differ:** `'' ` (empty string) vs `None` vs missing key.
  The helper normalises to '' for missing values so callers can
  do `if row.get('col')` safely.

## Composes with

- `/qualtrics-e2e-pressure-test` — uses this skill internally
- `/qualtrics-export` — for understanding the CSV schema
- `/qualtrics` — for survey-definition (questions/blocks) reads, not response data
