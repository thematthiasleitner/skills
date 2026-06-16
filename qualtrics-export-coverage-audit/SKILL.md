---
name: qualtrics-export-coverage-audit
description: Report every Qualtrics DataExportTag that will NOT appear in CSV exports — block-less questions (in no block) and questions in blocks unreached by the SurveyFlow. A question can be "alive" (exists + tagged) yet block-less → Qualtrics silently omits it from exports → its column vanishes downstream with zero error (the 2026-06 ADVANCE f_ty_room_N_t* slot-column vanish). Invoke BEFORE building any re-derive-from-CSV check / self-heal (confirm the column still exports), after any survey restructure that moves/detaches questions or blocks, or when a workbook column has silently gone empty and you suspect the survey, not the code. Read-only — pulls the live survey definition (or reads a saved JSON) and prints a verdict; mutates nothing.
---

# qualtrics-export-coverage-audit

**One job:** given a Qualtrics survey definition, list the `DataExportTag`s that
**will not export to CSV**. Two silent causes:

1. **Block-less** — the question is in no block's `BlockElements`. It is still
   "alive" (in the definition, has a tag) but Qualtrics omits block-less
   questions from every export. This is the silent killer.
2. **Unreached block** — the question's block exists but is not referenced by
   the `SurveyFlow`, so it never runs and never exports.

Why this exists: the 2026-06 address-first restructure detached the 20 legacy
`f_ty_room_N_t*` slot data questions from their block (re-using it for the new
`f_ty_addr_*` questions). They stayed alive but block-less → dropped from
exports → downstream workbook columns vanished for ~3 weeks with no error. See
memory `reference_qualtrics_orphaned_question_nonexport`.

## Use it

Bundled script `audit_export_coverage.py` does the parse. Two modes:

```bash
# Hermetic — against a saved survey-definition JSON (the `result` object,
# or a full {"result": …} response):
python3 audit_export_coverage.py --json /path/to/survey_def.json

# Live — pull SV_aWrEE8bXIdc6Pqe via the API (needs qualtrics_env.sh sourced):
set -a && source qualtrics/qualtrics_env.sh && set +a
python3 audit_export_coverage.py --survey SV_aWrEE8bXIdc6Pqe

# Filter to a tag family you care about:
python3 audit_export_coverage.py --survey SV_… --prefix f_ty_room
```

Exit code is **non-zero if any tagged question won't export** (so it doubles as
a CI/Layer-C gate). Output per non-exporting tag: the QID, the tag, and the
reason (`block-less` | `block <bid> not in flow`).

`--expect-missing tag1,tag2` whitelists tags you KNOW are intentionally retired
(e.g. legacy questions kept block-less on purpose) — they're reported but don't
flip the exit code. Use this to assert "only the columns I expect to be gone are
gone, nothing new."

## Get the survey JSON

If you don't already have it, **[/qualtrics-survey-pull](../qualtrics-survey-pull/SKILL.md)**
fetches the live definition; save its `result` and pass `--json`, or just use
`--survey` here (this script pulls it itself).

## Composes with

- **[/qualtrics-survey-pull](../qualtrics-survey-pull/SKILL.md)** — upstream source of the survey-definition JSON.
- **[/advance-add-layer-c-check](../advance-add-layer-c-check/SKILL.md)** — wrap this as a nightly drift tripwire (the audit is already exit-coded for it).
- **[/advance-durable-workbook-fix](../advance-durable-workbook-fix/SKILL.md)** — the downstream fix when a needed column HAS vanished: pin it from the last-good archive before relying on it again.

## Precondition

`--survey` mode needs `QUALTRICS_API_TOKEN` + `QUALTRICS_DATACENTER` in the env
(`source qualtrics/qualtrics_env.sh`). `--json` mode is fully offline.

## Self-verify

`runner.sh` runs the bundled script against `fixtures/survey_def_sample.json`
(one healthy tag, one block-less tag, one tag in an unreached block) and asserts
the block-less + unreached tags are flagged and the healthy one is not.
