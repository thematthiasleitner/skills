---
name: audit-hardcoded-drafts
description: Audit all hardcoded Outlook drafts for the ADVANCE project — verify each draft matches the participant's intervention, has a consistent stamp, contains the correct template content, and identify wrongly-created emails or code-level issues. Invoke when the user wants to check draft correctness, verify stamps, find misrouted drafts, or diagnose pipeline issues.
---

# Audit Hardcoded Drafts Skill

You audit **hardcoded drafts** (non-LLM, template-based) in the ADVANCE project's Outlook mailbox and produce a report identifying which drafts were wrongly created, which stamps are inconsistent, and what code-level issues might be causing problems.

**You never create or delete drafts yourself** unless the user explicitly asks. Your default output is a report. When the user asks for remediation, confirm before each destructive action.

---

## Context — ADVANCE hardcoded draft pipeline

Drafts are created by three scripts running in the hourly email cycle:

1. **`qualtrics/create_participant_outreach_drafts.py`** — creates:
   - `registration_confirmation` (on enrollment)
   - `consent_pre_invite` (confirmation + 1 day)
   - `prog_info_standard` / `prog_info_combined` / `prog_info_wcg` (7 days before course)
   - `prog_start-in-1-week_pod` / `_sh` / `_cog` / `_combined` (1–8 days before course)
   - `signout_confirmation` (when `signed_out=TRUE`)

2. **`qualtrics/create_questionnaire_reminder_drafts.py`** — creates:
   - `consent_pre_reminder_1` (5 days after invite stamp)
   - `consent_pre_reminder_2` (5 days after reminder_1 stamp)
   - post/fup-stage reminders (LLM-based, ignore for this audit)

3. **`qualtrics/create_initial_drafts.py`** — creates facility outreach drafts (not participant-facing)

Drafts live in the shared mailbox `advance-project@unige.ch` under:
```
Drafts/hardcoded/{role}/{template_name}/
```
where `role` is `part`, `part_PC`, or `facilities`.

### Intervention → template mapping

| Sheet | Intervention | prog_info | prog_start |
|---|---|---|---|
| part | POD | prog_info_standard | prog_start-in-1-week_pod |
| part | SH+ | prog_info_standard | prog_start-in-1-week_sh |
| part | COG | prog_info_standard | prog_start-in-1-week_cog |
| part | SH+ & COG | prog_info_combined | prog_start-in-1-week_combined |
| part_PC | (WCG) | prog_info_wcg | (none — WCG never attends) |

### Stamp columns

Each draft folder has a matching stamp column in the Excel sheet:

| Draft folder | Excel column |
|---|---|
| registration_confirmation | registration_confirmation_draft_at |
| consent_pre_invite | consent_pre_invite_draft_at |
| consent_pre_reminder_1 | consent_pre_reminder_1_draft_at |
| consent_pre_reminder_2 | consent_pre_reminder_2_draft_at |
| prog_info_* | prog_info_draft_at |
| prog_start-in-1-week_* | prog_reminder_draft_at |
| signout_confirmation | signout_confirmation_draft_at |

### Expected invite-phase chain

```
registration_confirmation_draft_at = X
  → part_pre_ques_inv = X + 1 (auto-normalized)
  → consent_pre_invite_draft_at = X + 1 (auto-normalized if backfilled)
  → consent_pre_reminder_1_draft_at >= invite + 5 days
  → consent_pre_reminder_2_draft_at >= reminder_1 + 5 days
```

---

## Step 0 — Setup

You need SSH access to the server (UNIGE VPN required):

```bash
# Ensure SSH key is in agent (if command fails)
ssh-add --apple-use-keychain ~/.ssh/ssh-key

# Sanity check
ssh -i ~/.ssh/ssh-key leitneruser@10.40.41.88 echo OK
```

If the SSH fails with permission denied, the key isn't in the agent. If it times out, the VPN is down and you should ask the user to reconnect.

---

## Step 1 — Run the audit script

The skill ships with `audit_script.py`. Copy it to the server and run it:

```bash
scp -i ~/.ssh/ssh-key ~/.claude/skills/audit-hardcoded-drafts/audit_script.py \
  leitneruser@10.40.41.88:/tmp/audit_script.py

ssh -i ~/.ssh/ssh-key leitneruser@10.40.41.88 \
  'cd email_draft_automation && .venv/bin/python3 /tmp/audit_script.py'
```

The script performs these checks and prints results grouped by issue type.

---

## Step 2 — Checks the audit performs

### A. Structural (draft ↔ sheet ↔ intervention alignment)

**Reminder:** since the DDD partitioning, dead rows (signed-out, bounced, superseded) live on `part_inactive`. The audit loads all three sheets — `part`, `part_PC`, `part_inactive` — but `active_row_for()` never returns a `part_inactive` row. Consult `docs/glossary.md` for the canonical lifecycle-state definitions.

1. **WRONG_INTERVENTION** — draft is in a folder that doesn't match the participant's intervention (e.g., POD participant with a draft in `prog_start-in-1-week_cog`).

2. **WRONG_SHEET** — draft is in `part/` for a participant whose active row is on `part_PC`, or vice versa.

3. **WCG_GOT_TREATMENT_DRAFT** — a `part_PC` (WCG) participant has a draft in any treatment folder (prog_start-*, prog_info_standard/combined). WCG only gets prog_info_wcg and consent/registration/signout drafts.

4. **TREATMENT_GOT_WCG_DRAFT** — a `part` participant has a draft in `prog_info_wcg`.

4.5. **DRAFT_FOR_INACTIVE_ONLY** — recipient exists only on `part_inactive` (no active row anywhere). The draft is stale: partition already moved the dead row, and current code won't regenerate anything for this recipient.

4.6. **DRAFT_FOR_NOT_ENROLLED** — active row exists but `part_enrolled`/`part_PC_enrolled` is FALSE. Current code creation guards require enrollment; the draft wouldn't be recreated. Exception: `signout_confirmation` — that template doesn't require enrollment.

### B. Stamp consistency

5. **DRAFT_WITHOUT_STAMP** — draft exists in Outlook but its matching Excel stamp column is empty. Cause: stamp write failed, or draft was re-created after stamp was cleared.

6. **MISSING_DRAFT** — stamp is set in Excel but no draft found in Outlook and no matching email in Sent Items. Could mean the draft was manually deleted without sending.

7. **STAMP_OUT_OF_ORDER** — for pre-invite chain, a later stamp has an earlier date than an earlier stamp (e.g., `consent_pre_reminder_2_draft_at` < `consent_pre_reminder_1_draft_at`). Signals a code-level overwrite bug.

8. **STAMP_PREDATES_CONFIRMATION** — `consent_pre_invite_draft_at` is earlier than `registration_confirmation_draft_at`. Signals a legacy backfill that wasn't cleaned up by the auto-normalizer.

### C. Content checks

9. **MISSING_PLACEHOLDER** — draft body contains unresolved placeholder (e.g., `{prog_date}`, `{salutation}`).

10. **POD_WITH_PLATFORM_TEXT** — prog_info draft to a POD participant contains `plateforme en ligne` text (wrong — only SH+/COG have the digital platform).

11. **TEMPLATE_CONTENT_MISMATCH** — body frequency text doesn't match folder:
    - `prog_info_standard` body should contain `toutes les deux semaines` (biweekly)
    - `prog_info_combined` body should contain `une fois par semaine` (weekly)
    - `prog_info_wcg` body should contain `liste d'attente` / `Warteliste`

### D. Duplicate / sent checks

12. **ALREADY_SENT** — draft has same subject as an email already in Sent Items to the same recipient. Cause: draft was sent, but somehow a new draft was created (stamp cleared, folder re-populated).

13. **DUPLICATE_DRAFTS** — same recipient has multiple drafts in the same folder.

### E. Row-level sanity (unexpected patterns)

14. **DUAL_ACTIVE_ROWS** — participant email appears on both `part` and `part_PC` with neither row marked as superseded. Signals a data integrity issue.

15. **DRAFT_FOR_SIGNED_OUT** — draft exists for a participant with `signed_out=TRUE` (other than a signout_confirmation draft).

16. **DRAFT_FOR_DEAD_ROW** — draft exists for a participant with `part_superseded_by` set or `email_postmaster_failure=TRUE`.

17. **REMINDER_GAP_TOO_SHORT** — `consent_pre_reminder_2_draft_at` is less than 5 days after `consent_pre_reminder_1_draft_at`. Signals that `should_create_reminder`'s min_gap_days guard didn't fire.

---

## Step 3 — Interpreting findings at the code level

Each issue type maps to a likely code-level cause. When writing the report, include this diagnosis:

| Issue | Most likely code-level cause |
|---|---|
| WRONG_INTERVENTION / WRONG_SHEET | Dual-sheet routing — check if `part_PC` row has `part_superseded_by` set. If yes, the superseded guard in `create_participant_outreach_drafts.py:220` should have caught it. If the draft is new, investigate whether that guard is being skipped. |
| DRAFT_WITHOUT_STAMP | Stamp-write race: draft created but the workbook save failed, or a parallel export cleared the stamp. Check if the draft is in a reply thread (stamping may fail with `ErrorInvalidPropertySet` — which is benign for stamp purposes). |
| MISSING_DRAFT | Draft was sent (check Sent Items) or manually deleted. If sent, the Sent Items search should find it — a true "missing" means deletion. |
| STAMP_OUT_OF_ORDER | A script overwrote a stamp it shouldn't have. Historically caused by `create_initial_drafts.py:send_questionnaire_invites()` — confirm that function is no longer called. |
| STAMP_PREDATES_CONFIRMATION | Legacy backfill from `part_pre_ques_inv`. The auto-normalizer in `create_participant_outreach_drafts.py:393-409` should fix these; if they persist, investigate whether the normalizer is running or whether `confirmation_sent_date` is being parsed correctly. |
| POD_WITH_PLATFORM_TEXT | Template content issue — the current `prog_info_standard` template (`context/templates/participant_email_templates.json`) should not contain platform text. If it does, remove it and consider a POD-specific template. |
| ALREADY_SENT | Dedup guard failure. The sent-guard at `create_participant_outreach_drafts.py:~501` should catch this. If it's not, verify the sent-items search is finding the right messages (check subject-fragment matching). |
| REMINDER_GAP_TOO_SHORT | `should_create_reminder` in `questionnaire_drafts_common.py:156` should block this via `min_gap_days`. If it's not, check that the caller in `create_questionnaire_reminder_drafts.py` passes `min_gap_days=reminder_days`. |
| DUAL_ACTIVE_ROWS | Superseded mechanism in `export_responses_to_contacts.py:3658-3676` didn't mark the older row. Investigate whether both rows have valid `part_recorded_date` values that would allow dedup comparison. |
| DRAFT_FOR_SIGNED_OUT / DRAFT_FOR_DEAD_ROW | Dead-row guard at `create_participant_outreach_drafts.py:220` missed it. Check if the row has `part_superseded_by` populated as expected. |

---

## Step 4 — Write the report

The report MUST include:

1. **Executive summary** — one-line count of issues per type (use the table above).
2. **Wrongly-created drafts** — an itemised list with recipient, folder, and diagnosis.
3. **Code-level issues** — grouped by likely cause, with the file + line reference from the table above.
4. **Recommended actions** — split into:
   - *Delete these drafts in Outlook* (already-sent duplicates, wrong-intervention drafts)
   - *Set these stamps in Excel* (drafts without stamps, where content is actually correct)
   - *Fix code* (with file + line suggestions)

Write the report to `temp1.md` unless the user specifies another path.

**Do NOT produce a blanket "delete everything flagged" recommendation.** Each flagged draft should be investigated to confirm the diagnosis. Historical draft audits in this codebase have had false positives — particularly for WRONG_INTERVENTION on dual-sheet participants (where the superseded `part_PC` row made a treatment participant appear WCG).

---

## Step 5 — If the user asks to fix issues

Before taking destructive action (delete draft, clear stamp, overwrite data):
1. Verify the diagnosis by reading the actual email content (not just the folder path).
2. Confirm with the user what to delete before issuing `DELETE` requests.
3. For stamp fixes, prefer setting stamps (stops re-creation) over clearing them (triggers re-creation).

When deleting drafts, always verify Sent Items first:
```python
resp = mail._request('GET', f'/users/{mailbox}/mailFolders/SentItems/messages',
                     params={'$search': f'"to:{email}"', '$top': '20',
                             '$select': 'subject,sentDateTime'})
```
Never delete a pending draft unless you have confirmed either:
- the email was already sent (duplicate), or
- the draft is structurally wrong (wrong template/recipient) AND the user confirms.

---

## Reference: server and Excel locations

| What | Where |
|---|---|
| Server SSH | `ssh -i ~/.ssh/ssh-key leitneruser@10.40.41.88` (UNIGE VPN required) |
| Workbook (live) | `~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx` |
| Templates JSON | `~/email_draft_automation/context/templates/participant_email_templates.json` |
| Mailbox | `advance-project@unige.ch` (via Microsoft Graph, `build_graph_service_from_env`) |
| Graph wrapper | `email_draft_automation/src/graph_mail.py` |

---

## Reference: the audit script

The reference script `audit_script.py` next to this SKILL.md implements all of Step 2's checks. Read it before running — you may want to narrow the scope (e.g., one template family, one participant) rather than running the full audit for every question.
