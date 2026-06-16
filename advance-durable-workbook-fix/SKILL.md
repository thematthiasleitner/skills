---
name: advance-durable-workbook-fix
description: Decide + scaffold a DURABLE fix to the format/content of cells in the ADVANCE live workbook (Qualtrics_ADVANCE_recruitment_live.xlsx). Encodes the hard-won lesson that a one-time --apply "sweep" of the live workbook is SILENTLY REVERTED by rclone bisync on the next cycle (the cycle's initial rclone_excel_sync re-pulls the stale OneDrive peer), so it routes you to the durable mechanism instead — normalise-at-writer for rebuilt sheets, an in-export self-heal pass for append-only source sheets, or a one-time sweep ONLY under a paused cycle. **Medium/high-risk (touches live workbook) — propose via AskUserQuestion, never silently apply a live mutation. Composes advance-lock + workbook-format-census.** Invoke whenever the task is "fix / normalise / backfill / migrate these workbook cells" and the fix must persist across the 15-min cycle + rclone bisync.
tools: Bash, Read, Edit, Write
---

# ADVANCE Durable Workbook Fix

You design a workbook data/format fix that **survives the 15-min cycle and rclone
bisync**. The trap this skill exists to prevent (observed live 2026-06-04 during
the ADR-0002 date/time standardisation): a one-time `--apply` sweep of the live
workbook was reverted on the very next cycle, because the cycle runs an initial
`rclone_excel_sync` that re-pulls the **stale OneDrive peer** over the server's
freshly-edited file. **Append-only protects against the *export* rewriting rows;
it does NOT protect against *bisync* overwriting the whole file from a stale peer.**

## The core decision (do this FIRST, before writing any mutation)

Classify the target column with `/workbook-format-census` (which sheet, value
distribution, MIXED?), then route:

1. **Derived / rebuilt-every-cycle sheet** (`list_rooms`, `course_summary`,
   `part`/`part_PC`/`part_inactive` `part_prog_*`, `questionnaire_summary`,
   `trai_*_summary`):
   → **Normalise at the writer.** The sheet is `delete_rows` + rebuilt each cycle,
   so wrapping the write (e.g. `normalize_date_ddmmyyyy(...)`) makes it self-heal.
   **No sweep needed, no live edit needed** — deploy the code; the next cycle fixes it.

2. **Append-only SOURCE sheet** (`f_ty_2_con`, `admin_rec_con`, `trai_onl`,
   `trai_in-p` — written via `append_unique`, existing rows preserved):
   → **Add an in-export SELF-HEAL pass**, NOT a one-time sweep. Pattern:
   `canonicalize_existing_datetime_cells(ws, header, col_normalisers)` in
   `export_responses_to_contacts.py` (the ADR-0002 reference implementation),
   called right after the `append_unique` for that sheet. It re-applies the
   canonical form to EXISTING cells in place **every cycle**:
   - idempotent (only writes when the value changes → no bisync churn once clean);
   - skips manual-override-filled cells (`MANUAL_OVERRIDE_FILL_COLOR`);
   - runs at the END of the workbook build, so the cycle's final `rclone_excel_sync`
     pushes canonical to OneDrive → all peers converge and STAY converged.
   This is **bisync-proof**: even if a cycle starts from a stale peer, the export
   re-heals before the final push.
   (Note: `trai_*` already self-heal because `rebuild_training_sheet` rewrites them
   wholesale — verify before adding a redundant pass.)

3. **One-time sweep** (`tools/sweep_datetime_canonical.py`-style, `--dry-run`
   default): valid ONLY for truly frozen historical data AND only with the
   **cycle paused** (so no bisync runs during/after) — which needs the sudo
   passphrase (`reference_manual_cycle_control`). Otherwise it WILL be reverted.
   Keep such scripts as one-shot diagnostics; prefer option 2 for durability.

**Rule of thumb:** if the fix must persist on a live, bisynced, cycling workbook
and you can't guarantee a paused cycle, make it a **self-heal in the export**, not
a one-time edit.

## Workflow

1. **Census** the target columns: `/workbook-format-census` (or an openpyxl scan)
   → which sheets, current value/format distribution, manual-owned cells. Decide
   Family-A-style "normalise" vs leave-alone (ISO machine stamps, embedded
   course_id dates, durations) — see ADR 0002 for the canonical taxonomy.
2. **Route** each column via the decision above (derived / source / frozen).
3. **Implement** the chosen mechanism on a branch in a clone (see
   `advance-agent-session` first to avoid shared-tree/shared-lock hazards):
   - writer-normalise and/or a self-heal pass (idempotent, skip-manual);
   - write regression tests (Layer A: dot/int → canonical; idempotent 2nd pass = 0;
     manual cell skipped; canonical/unparseable untouched);
   - update/author the ADR documenting the reversal/decision.
4. **Test gates** (`make test-a` + `test-headers` + `test-b`) green for your change.
5. **Deploy** (`/advance-deploy`) → **verify on a live cycle**: the export should
   log `self-healed N cells`, and a post-cycle census / sweep dry-run should read
   **0 remaining**. One cycle proves it fired; idempotency guarantees durability.

## Why NOT just sweep + pause every time

A sweep+pause is a manual, sudo-gated, one-shot operation that re-dirties the
moment any future stale-peer bisync occurs. The self-heal is set-and-forget:
it re-converges automatically, needs no sudo, and protects against future drift.

## Safety invariants

- **Never silently apply a live-workbook mutation.** Propose via AskUserQuestion;
  the actual `--apply` / live edit needs explicit consent + the agent-lock.
- **Skip manual-owned cells** (red/dark-red fill, `MANUAL_OVERRIDE_FILL_COLOR`).
- **Leave Family-B alone**: ISO machine stamps (`*_at`, `*_draft_at`,
  `part_recorded_date`, `*_fini_date`, `part_prog_info_due` gate,
  `template_matrix.*_due/_created/_sent`, `sent_log`), `course_id`-embedded ISO,
  durations. See ADR 0002 §scope.
- **Idempotent or it churns bisync.** A self-heal/sweep that rewrites identical
  values every cycle updates mtime → triggers a needless bisync each cycle.
  Only write when the value actually changes.
- **Test the manual-skip + idempotency**, not just the happy path.

## Composes with

- `/workbook-format-census` — classify the target columns first
- `/advance-agent-session` — set a distinct agent id + verify clone safety before editing
- `/advance-lock` — hold the mutex for any live edit
- `/advance-deploy` — ship the self-heal/writer change
- `/advance-server-cycle-trigger` — force a cycle to verify the self-heal fired
- ADR `docs/adr/0002-workbook-date-time-standardisation.md` — the reference
  implementation (`canonicalize_existing_datetime_cells`) + the bisync addendum
