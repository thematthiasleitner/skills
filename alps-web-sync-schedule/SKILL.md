---
name: alps-web-sync-schedule
description: Update an ALPS event programme / day-by-day timetable on the website from a planning spreadsheet. Use when the user has edited the schedule in a planning XLSX and wants the website's programme updated, or mentions timetable/programme/schedule changes for an ALPS site (e.g. summerschool.alps.foundation). Reads a planning tab laid out as per-day 3-column blocks (time | speaker/title | topic) with openpyxl — handling the shared leftmost time column fallback — then maps the requested changes into the site's schedule[] data array. Discovers the sheet and tab and confirms ambiguous/internally-inconsistent times; never resyncs unrequested days silently. Composes with alps-web-ship to build + deploy.
---

# Sync an ALPS programme from a planning sheet

Composable on top of **alps-web-ship**. Discover the sheet; change only what's asked; ask when the sheet is ambiguous.

## 1. Locate the planning sheet (discover + confirm)

- Search the Drive rather than hardcoding: `find ~/Library/CloudStorage -maxdepth 7 -iname '*planning*xlsx' -o -iname '*program*xlsx' 2>/dev/null`.
- If 0 or several matches, or the tab name is unclear → **AskUserQuestion** (which file / which tab). Note the **mtime** — if the user "just edited it", Drive sync can lag and your local copy may be stale; say so if the content looks unchanged.

## 2. Read the tab

`python3 scripts/read_program_sheet.py <file.xlsx> --sheet Program [--day Thursday]`

The tab is laid out as per-day **3-column blocks** (time | who | topic). A blank per-day time cell **falls back to the shared leftmost time column**. The script prints each day's rows so you can diff against the site.

## 3. Map into the site's schedule

- Find the schedule data in the repo (e.g. a `schedule` / `days` array in a Program component): `grep -rn "sessions:\|schedule\b" src/components`.
- **Change only what the user asked** (e.g. "I updated Thursday"). Do NOT re-sync every day from the sheet — the sheet often differs from the site in ways that aren't intended changes.
- Preserve the site's own fields/conventions (`kind`, titles, anchor derivation). Many ALPS sites auto-derive `#day-N` / slot / `#speaker-<slug>` anchors from the data — just edit the entries; anchors follow.
- Keep speaker **names** byte-identical to the existing entries so any name-based schedule↔bio linking keeps resolving.

## 4. Resolve ambiguous / inconsistent times — ask, don't guess

Planning sheets are often internally inconsistent (e.g. a "Lunch" row at 13:00–14:00 that overlaps a 13:30 workshop) or stale (Drive lag). If the times don't form a clean non-overlapping sequence, present what you read and **AskUserQuestion** for the exact times rather than inventing them. Flag any assumption in the PR body.

## 5. Ship

Hand off to **alps-web-ship**: build (exit 0), grep the built HTML for the changed text, PR → merge → poll live. Call out any time you had to infer for the user to confirm before/after merge.
