---
name: archive-stale
description: Walk any folder tree and archive stale artefacts (versioned predecessors, _BEFORE/_PREV snapshots, .pre_* files, _old_* markers, dated duplicates, abandoned trial/test runs) into per-folder `archive/<date>-cleanup/<category>/`. Dry-run by default, --apply moves files. Use when the user wants to tidy / clean up / organize an output folder, archive stale files, or recover signal after a long session left behind intermediate artefacts. **Medium-risk (mutates filesystem when --apply is passed) — ALWAYS dry-run first, show the plan, get explicit consent before `--apply`.**
---

# archive-stale

Tidy a folder tree by detecting stale artefacts and moving them into per-folder archive subdirectories. Defaults to dry-run so the user can review every proposed move.

## Quick start

```bash
# 1. Dry-run on a target tree — prints a plan, moves nothing
python ~/.claude/skills/archive-stale/scripts/archive_stale.py <target_dir>

# 2. After the user reviews the plan and approves:
python ~/.claude/skills/archive-stale/scripts/archive_stale.py <target_dir> --apply
```

## What counts as "stale"

The script applies these detectors per folder (each item is categorised; the user sees the category in the dry-run plan):

| Category | Pattern | Example |
|---|---|---|
| `versioned_predecessors` | `foo_v1`, `foo_v2`, …, `foo_vN-1` when `foo_vN` exists | `accent_audit_v3` archived if `accent_audit_v5` exists |
| `snapshot_intermediates` | `*_BEFORE.*`, `*_PREV.*`, `*_PREV2.*`, `*.pre_*.*`, `*_pre_*.*` | `Innere_Balance_review_PREV.xlsx` |
| `old_marker` | `old_*`, `*_old.*`, `*_old_*` | `SH+_old_script_structured.json` |
| `dated_duplicates` | `<base>_YYYYMMDD*` clusters — keep newest, archive rest | `plan_20260513-*` archived if `plan_20260527-*` exists |
| `trial_runs` | `trial_*`, `*_trial_*` (older than 30 days) | `trial_gemini_2.5_flash/` |
| `numbered_iterations` | `report.json` + `report_clean.json` + `report_final.json` + `report_post_*.json` cluster | 5 `COG_chunk_drift_report*.json` variants |

## Safety contract

The script **never** touches:
- Hidden files (`.git`, `.DS_Store`, `.venv`, …)
- Anything already inside an `archive/` subdirectory
- Anything inside `node_modules`, `__pycache__`, `.git`, `dist`, `build`
- The "current" item in each detected cluster (newest version, highest-numbered variant)
- Empty directories (left alone — not enough signal)

The script **default-dry-runs**:
- Prints `WOULD ARCHIVE` lines with full source + destination paths
- Prints a summary table grouped by category
- Exits 0 without moving anything

Pass `--apply` to actually move. Each folder that gets items archived gets its own `archive/YYYYMMDD-cleanup/<category>/` subdir.

## Workflow

1. Run dry-run on the target directory:
   ```bash
   python ~/.claude/skills/archive-stale/scripts/archive_stale.py <target> [--max-depth N] [--min-age-days N]
   ```
2. Show the user the full plan output (or a summary if huge).
3. **Always ask explicit confirmation via `AskUserQuestion`** before running with `--apply`. Offer at least one alternative ("skip this", "narrow scope", "show full list").
4. On approval, run `--apply` and report counts.

## Options

| Flag | Default | Effect |
|---|---|---|
| `--apply` | off | Actually move files. Without it, dry-run only. |
| `--max-depth N` | 8 | Limit recursion depth from target root. |
| `--min-age-days N` | 0 | Skip items modified within last N days (use 7-30 to be conservative). |
| `--include-trial-younger` | off | Allow `trial_*` dirs younger than 30 days to be archived. |
| `--label LABEL` | `cleanup` | Customise the dated subdir name: `archive/YYYYMMDD-<label>/`. |
| `--only CATEGORY[,…]` | all | Restrict to specific categories (e.g. `--only snapshot_intermediates,old_marker`). |

## When NOT to invoke this skill

- The user wants to **delete** files (this skill only moves to archive)
- The user wants to **rename** files (this is move-with-categorisation, not refactor)
- The folder is a git working tree with staged-but-uncommitted moves at stake — git tracks renames but the user should commit first
- The target is `/`, `$HOME`, or any system directory — refuse and ask for a narrower target

## What success looks like

After `--apply`, the target folder contains only **current** artefacts at top level. Stale items live under `<folder>/archive/<date>-cleanup/<category>/` and can be retrieved trivially. Each subfolder that contains stale items gets its own archive, matching the per-folder convention the user asked for during the 2026-06-01 `outputs/` cleanup.
