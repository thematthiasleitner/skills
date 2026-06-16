---
name: qualtrics-response-audit
description: READ-ONLY audit of live ADVANCE Qualtrics responses by status — list them with RecordedDate, profile, email, and whether each carries the @advance-test.invalid test-marker (so you can tell real recruitment data from leftover test imports). Wraps email_draft_automation/tools/audit_status4_responses.py. Use before cleaning up imported/test responses, before relaxing or sanity-checking the live status gate, or any time you need to answer "what responses of status X are in the survey, and which are real vs test?". Low-risk (no mutation, no lock) — but it talks to live Qualtrics.
---

# qualtrics-response-audit

A read-only lens on the live survey's responses: who's in there, when, and —
critically since the Status=4 gate (the marker is now the sole live-exclusion) —
which rows are **real** vs **test-marker** (`@advance-test.invalid`). Use it to
decide what's safe to delete and to confirm the survey is clean before/after a
gate change.

No mutation, no agent-lock needed. It only GETs the responses export.

## Run

```bash
cd <clone>/email_draft_automation
set -a && source qualtrics/qualtrics_env.sh && set +a
.venv/bin/python3 tools/audit_status4_responses.py
```

Output: every **Status=4 (Imported)** response with `RecordedDate`,
`ResponseId`, a `MARK` flag (marker email / trai_onl trainer-name marker), and
the email; plus a `marker-emailed vs non-marker (real)` tally. The **non-marker**
rows are the ones that WOULD enter live under the relaxed `0,4` gate — review
those first.

## When to use

- **Before a Status=4 cleanup** — see exactly which imports exist and which are
  real before deleting (deletes are irreversible; do those under the agent-lock
  via the responses API `DELETE /surveys/{id}/responses/{rid}`).
- **Before relaxing / after sanity-checking the live status gate** — confirm 0
  unexpected non-marker imports (pairs with Layer C `status-gate` +
  `no-test-marker-in-live`).
- **Debugging "why is this row in/not in live?"** — status + marker together
  explain it (see `response_enters_live` in export_responses_to_contacts.py).

## Extending to other statuses

The shipped tool targets Status=4 (the import-cleanup case it was written for).
To audit a different status (e.g. 0/IP-Address, 1/Preview), copy its
`status_code(st) != "4"` filter and change the target — the marker logic
(`is_test_marker_email` / `row_has_test_marker`) is status-agnostic and reused
from the export module.

## Composes with

- `/qualtrics-inject-row` — after injecting a real Status=4 row, audit to confirm it landed
- `/advance-cycle-status` — confirm the audited state materialised in the live workbook
- Layer C `status-gate` + `no-test-marker-in-live` — the nightly invariants this audit checks ad-hoc
