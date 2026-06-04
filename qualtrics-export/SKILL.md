---
name: qualtrics-export
description: Expert knowledge of the ADVANCE project Qualtrics export pipeline — CSV column format, f_ty_room naming conventions, export script architecture, and diagnosing missing rows. Invoke when the user asks about CSV exports, missing rows, the export script, or f_ty_room columns.
tools: Bash, Read, Glob, Grep
---

# Qualtrics Export Skill

You are an expert at the ADVANCE project's Qualtrics export pipeline. When this skill is
invoked, help the user work with CSV exports from Qualtrics and the export script.

Complements `/qualtrics` (which covers the Qualtrics REST API). This skill covers the
**CSV output format** and **`export_responses_to_contacts.py`** script internals.

---

## ⚠️ Rule: when updating or working on COLUMNS, consult BOTH the CSV and the JSON

A column **cannot** be reasoned about from code alone. Before adding, removing,
renaming, or "fixing" any column, consult **both** live artifacts together:

1. **The Qualtrics export CSV** (`/qualtrics-csv-pull`, or `qualtrics/pull_export_csv_latest.py`)
   — *is the field still arriving, and what values come in?* A column can be code-ALIVE
   but perpetually blank because its CSV field stopped coming.
2. **The survey-definition JSON** (`/qualtrics-survey-pull`) — *does the source question
   still exist, is it in a live block or orphaned, what format/validation does it enforce?*
   A question can be deleted or moved out of every block ("dead") while the column lingers.

Code + CSV alone misses deleted questions; code + JSON alone misses fields that stopped
arriving. **Both, every time.** `/qualtrics-column-trace` runs both (plus the code + the
workbook) in one shot — prefer it for any column audit. This rule is the lesson of the
`part_zoom` dead-column and `f_ty_2_con` format-drift audits (2026-06-04).

The CSV is consumed **label-based** (`useLabels=True`): fields are TEXT, not numeric
recode values. Tune all column code to the label form — see ADR 0003 and
`/label-numeric-audit`.

---

## CSV structure

The exported CSV has **three header rows** (the export pulls `useLabels=True`):
- Row 1: API field names (`DataExportTag` values) — used for all code references
- Row 2: Human-readable question text
- Row 3: `{"ImportId":...}` metadata
- Row 4+: Data rows

`read_csv_from_zip` takes fieldnames from row 1 and slices `rows[3:]` so rows 2+3
are dropped. **Bare `csv.DictReader` does NOT do this** — it treats rows 2+3 as
data (2 phantom rows). Always go through `read_csv_from_zip`.

**Qualtrics built-in columns** — values shown are the `useLabels=True` form
(TEXT labels), which is what production actually downloads:

| Column | Values (useLabels=True) | Notes |
|--------|--------|-------|
| `ResponseId` | `R_...` | Unique response ID |
| `Status` | **`IP Address`** (live), **`Survey Preview`** (preview), **`Imported`** (API) — TEXT, not `0`/`1` | Per ADR 0003 `qualtrics_status` stores this **label text**; the live preview-filter re-derives the numeric code via `status_code()`/`normalize_status` and keeps only the IP-Address (`0`) form (`QUALTRICS_STATUS_TARGET` stays numeric). Use `is_live_response(row)` — **never compare raw `Status == "1"`** (dead under labels). |
| `Finished` | **`True`** / `False` (text) | `is_finished()` accepts `1`/`true`/`yes`. Only finished is processed. |
| `StartDate` / `EndDate` | ISO datetime | UTC |
| `Q_Language` | `DE`, `FR` | Respondent language |
| `RecipientEmail` | email | Distribution email (may be empty) |

---

## f_ty_room column naming (facility room data)

Room data uses **two formats** in the CSV (both supported by the export script):

### New format (current surveys)
```
{room_idx}_f_ty_room_{attr}          — room base attribute
{room_idx}_f_ty_room_N_t{time_idx}_{field}  — timeslot attribute
{room_idx}_f_ty_room_N_t             — count of timeslots for this room
```

Examples:
- `1_f_ty_room_addr` — address of room 1
- `2_f_ty_room_cap` — capacity of room 2
- `1_f_ty_room_N_t` = `"2"` — room 1 has 2 timeslots
- `1_f_ty_room_N_t1_begin` — room 1, timeslot 1, start date (dd/mm/yyyy)
- `1_f_ty_room_N_t2_time` — room 1, timeslot 2, time (HH:MM)

### Old/parenthetical format (legacy surveys, still supported)
```
f_ty_room_{attr}({room_idx})         — room base attribute
f_ty_room_N_t{time_idx}_{field}({room_idx})  — timeslot attribute
```

### Room base attributes
| Field suffix | Description |
|-------------|-------------|
| `canton` | Swiss canton |
| `city` | City with postal code |
| `addr` | Street address |
| `cap` | Capacity (integer) |
| `price` | Rental cost |
| `table` | Tables available |
| `WC` | Toilets |
| `elec` | Electricity |
| `speak` | Speaker system |
| `wifi` | WiFi |
| `wheel` | Wheelchair accessible |
| `PT` | Public transit nearby |
| `water` | Water access |

### Timeslot fields
| Field suffix | Description |
|-------------|-------------|
| `begin` | Start date (dd/mm/yyyy) |
| `day` | Weekday name (DE: Mittwoch / FR: Mercredi) |
| `time` | Time of day (HH:MM) |
| `weeks` | Duration in weeks |
| `hours` | Hours per session (float) |

---

## Export script architecture (`qualtrics/export_responses_to_contacts.py`)

### Entry point
```bash
source qualtrics/qualtrics_env.sh
QUALTRICS_WORKBOOK_MODE=live INSIDE_AUTOMATION_CYCLE=1 \
  .venv/bin/python3 qualtrics/export_responses_to_contacts.py
```

### Key functions

**`detect_block(row)`** — classifies a CSV row into a survey type:
- Priority order: `f_tor_3` > `f_tor_2` > `f_ty_1` > `f_tor_1` > `f_ty_2` > `f_tor` > `participant` > `part_int`
- Returns sheet name string (e.g. `"f_ty_2"`, `"participant"`) or `""`

**`build_f_ty2_rows_from_response(row, header)`** — splits 1 facility response into N Excel rows:
- One row per room-timeslot combination
- A response with 2 rooms × 2 timeslots → 4 rows
- Returns list of dicts matching `F_TY2_HEADER`

**`publish_survey(cfg)`** — publishes the survey after all updates:
- Called at end of `main()` after all choice updates and workbook sync

**`append_unique(ws, header, rows, dedup_by_response=False)`** — adds rows to a sheet:
- For `f_ty_2_con`: called with `dedup_by_response=False` (dedup by full row tuple, not RID)

### Status filter
- **Live mode** (`QUALTRICS_WORKBOOK_MODE=live`): `status_target = "0"` — only Status=0 rows processed
- **Preview/sandbox mode**: `status_target = "1"`
- Status=1 always means a preview/test response — never process in live workbook

### f_ty_2_con deduplication
- `existing_rids_ty2`: set of ResponseIds already in the Excel sheet, loaded at script start
- If a RID is in `existing_rids_ty2`, the entire response is skipped
- **To fix incomplete rows**: delete the incomplete row(s) from the Excel, then re-run export

---

## Diagnosing missing f_ty_2_con rows

1. **Check Status**: only `0` is processed in live mode.
2. **Check existing_rids_ty2**: if the ResponseId is already in the Excel sheet (even with incomplete data), it won't be reprocessed. Delete the incomplete row(s) from Excel and re-run.
3. **Check timeslot column format**: `{room_idx}_f_ty_room_N_t{time_idx}_{field}` — all 5 timeslot fields (`begin`, `day`, `time`, `weeks`, `hours`) should be present per timeslot.
4. **Check Finished**: only `Finished=1` responses are processed.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `QUALTRICS_API_TOKEN` | API authentication |
| `QUALTRICS_DATACENTER` | Base URL (e.g. `https://fra1.qualtrics.com/API/v3`) |
| `QUALTRICS_SURVEY_ID` | Survey ID (`SV_aWrEE8bXIdc6Pqe`) |
| `QUALTRICS_WORKBOOK_MODE` | `live` or `preview`/`sandbox` |
| `INSIDE_AUTOMATION_CYCLE` | Set to `1` when running from automation scripts |

All set by `source qualtrics/qualtrics_env.sh`.

---

## Composes with (column-work toolkit)

| Skill | Use for |
|---|---|
| `/qualtrics-csv-pull` | pull live response DATA (the CSV half of the column rule) |
| `/qualtrics-survey-pull` | pull live survey DEFINITION JSON (the JSON half; is a question alive/orphaned?) |
| `/qualtrics-column-trace` | **trace one column across survey → CSV → code → workbook in one shot** — the go-to for column audits |
| `/workbook-format-census` | census date/time/number formats across all sheets; flag MIXED columns |
| `/label-numeric-audit` | find numeric assumptions on the label-based CSV (dead `Status=="1"` guards, bare `DictReader`) |
| `/qualtrics-restructure-step` | actually MUTATE the survey (add/rename/delete a question) |

Governing decision: `docs/adr/0003-label-based-csv-consumption.md` (CSV consumed
label-based; one tolerant normalizer per semantic field; no numeric-export interpreter).
