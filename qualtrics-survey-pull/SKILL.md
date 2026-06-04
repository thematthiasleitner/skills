---
name: qualtrics-survey-pull
description: Pull the live ADVANCE Qualtrics survey DEFINITION (questions, blocks, flow) as JSON and answer "is this question still alive?" — its QID, type, validation/date-format, which block it's in, and whether that block is reachable in the SurveyFlow. Read-only — no Qualtrics state is mutated. The sibling to /qualtrics-csv-pull (which pulls response DATA). Invoke whenever a task needs the survey STRUCTURE rather than respondent data — checking whether a column's source question still exists or was deleted, whether a question is orphaned (in no block → dead), what date/time format a field enforces, or saving a dated definition snapshot before/after a survey edit. Encodes the QUALTRICS_DATACENTER-is-a-full-URL gotcha that causes a double-scheme crash when hand-rolled.
tools: Bash, Read, Glob, Grep
---

# Qualtrics Survey-Definition Pull Skill

You pull the live ADVANCE survey **definition** (`GET /survey-definitions/{id}`)
and answer structural questions about it. Read-only.

**Composability:** the structural half of column work. Pair with
`/qualtrics-csv-pull` (response data) — together they answer "does the code
expect the right thing, and is that thing still gathered on Qualtrics?".
Used by `/qualtrics-column-trace` (you don't need to invoke this separately if
you're running that). Complements `/qualtrics` (REST API reference) and
`/qualtrics-export` (CSV schema).

---

## When to invoke

- "Is `part_zoom`'s question still on the survey, or was it deleted?"
- "What date format does `f_ty_room_N_t1_begin` enforce?"
- "Is this question in an active block or orphaned?"
- "Snapshot the survey definition before/after my edit."
- Any column audit that must check the **survey side**, not just code + CSV.

## When NOT to invoke

- For respondent values → `/qualtrics-csv-pull`.
- To **edit** the survey (add/rename/delete questions, flow) → `/qualtrics` +
  `/qualtrics-restructure-step`.

---

## The one gotcha this skill exists to encode

`QUALTRICS_DATACENTER` (from `qualtrics_env.sh`) is the **full base URL**
(`https://fra1.qualtrics.com/API/v3`), **not** the bare datacenter id `fra1`.
Hand-rolling `f"https://{QUALTRICS_DATACENTER}.qualtrics.com/..."` produces a
double-scheme URL (`https://https://fra1...`) and a DNS crash. The helper reads
it correctly. Also: use `requests` (bundles certs), **not** `urllib` — system
Python fails SSL verification against `fra1`.

---

## Workflow

The logic lives in [_survey_pull.py](_survey_pull.py). Run it from inside
`email_draft_automation` with the env sourced:

```bash
cd email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a

# Pull + save dated JSON + summary (questions / blocks / orphaned count):
python3 ~/.claude/skills/qualtrics-survey-pull/_survey_pull.py

# Report ONE question by DataExportTag (liveness + format), no file written:
python3 ~/.claude/skills/qualtrics-survey-pull/_survey_pull.py --no-save --tag part_zoom
```

As a Python import:
```python
import sys; sys.path.insert(0, str(Path.home() / '.claude/skills/qualtrics-survey-pull'))
from _survey_pull import pull_survey_definition, question_report, blocks_in_flow
result = pull_survey_definition()
print(question_report(result, "f_ty_room_N_t1_begin"))
```

### What `--tag` / `question_report` returns
`{found, qid, type (QType/Selector/SubSelector), block (or "<NO BLOCK — orphaned/dead>"),
in_flow, validation (ContentType/ValidDateType/ForceResponse), question_text}`.

`block == "<NO BLOCK>"` is the decisive **dead-question** signal: a question in
no block cannot be shown to any respondent, so it collects nothing going
forward (e.g. the legacy `f_ty_room_N_tM_*` block — 22 orphaned questions as of
2026-06-04).

---

## Safety invariants

- **Read-only.** GET only — never POST/PUT here (that's `/qualtrics-restructure-step`).
- **Snapshot, don't trust a stale one.** A saved JSON is a point-in-time copy;
  re-pull if the survey may have changed since.
- **`in_flow` is conservative.** It walks `SurveyFlow` for `Block` nodes;
  blocks reached only via BlockRandomizer still count. `block == "<NO BLOCK>"`
  is the reliable dead signal — `in_flow=False` alone is not (a live block can
  read as out-of-flow if nested oddly), so trust the block-membership check.

## Composes with

- `/qualtrics-csv-pull` — the response-data half; run both for column audits.
- `/qualtrics-column-trace` — uses this skill internally.
- `/qualtrics-export` — CSV schema + the "always consult CSV **and** JSON when
  working on columns" rule.
