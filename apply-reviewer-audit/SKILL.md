---
name: apply-reviewer-audit
description: Apply a reviewer-edited audit XLSX to the ADVANCE translation block store safely. Snapshots impacted block-store dirs, dry-runs the classification, applies overrides + approvals, surfaces skip_note_only rows with glossary suggestions for per-row decisions, then optionally regenerates the downstream artifact (website JSON DB or manual DOCX) with confirmation. Invoke when the user wants to land reviewer feedback from an audit XLSX (Vitalité/Sérénité websites, COG_CB/CG manuals, or any future ADVANCE translation program with the same audit schema).
---

# apply-reviewer-audit

Land reviewer-edited audit XLSX feedback onto the ADVANCE translation block store, with safety rails the maintainer would otherwise have to wire up by hand each time.

## When to invoke

The user typed `/apply-reviewer-audit` OR asks something like "apply the audit / reviewer feedback / corrections in [some XLSX] to the [program]". The audit XLSX comes from `translation/scripts/audit_quality.py` and has the columns: `reviewer_certified`, `reviewer_corrected_de`, `reviewer_note`, `force_retranslate`, `file_sha8`, `block_id`, `status`, `fr_text`, `de_text`, `qc_summary`, `judge_verdict`, `judge_rationale`.

Repo root: `/Users/matthias/Library/CloudStorage/OneDrive-UniversitédeGenève/RA HORIZON/translation/`.

## Hard constraints (encode in every run)

1. **Always snapshot before write**. Back up every impacted `outputs/blocks/<sha8>/` directory to `/tmp/<sha8>.bak/` before calling `apply_reviewer_feedback.py`. Print the backup path so a rollback is one `cp -r` away.
2. **Never auto-run `scripts/reqc_block_store.py`** after apply. Known bug: it ignores `provenance.note=reviewer_override` and would re-flag just-approved blocks. Skip it. If the user explicitly asks for re-QC, warn first.
3. **Never auto-trigger Gemini retranslate or LLM judge** to resolve note-only rows. Per `translation/CLAUDE.md` ("Translation pipeline modes — ALWAYS ASK FIRST"), surface the choice via AskUserQuestion before any LLM call.
4. **Never recapture goldens to make tests pass** (per `feedback_authentic_over_byte_equality.md`). If a diff looks unexpected, stop and ask.
5. **Always confirm before regenerating the downstream artifact** (JSON DB for websites, DOCX for manuals). The block-store write is idempotent and reversible from backup; the regen produces user-visible deliverables.

## Workflow

### Step 1 — Validate inputs

- User passes (or you ask for) the path to the reviewer-edited audit XLSX. Examples: `de_translation_sources/website/vitalite_audit_819blocks.xlsx`, `de_translation_sources/manuals/COG_CB_audit_v2.xlsx`.
- Verify the file exists and is readable.
- Read its `file_sha8` column to figure out which block-store dirs will be touched. Usually just one sha8 per XLSX, but the importer tolerates multiple sheets / mixed sha8s.
- Cross-reference each sha8 against `~/.claude/skills/apply-reviewer-audit/program_map.json`. For each known sha8, you have the program name + regen recipe. For each **unknown** sha8: stop and ask the user how to regenerate that program's downstream artifact. The apply step can still run; only the regen recipe is missing.

### Step 2 — Snapshot

Run a quick Bash command to back up each impacted store dir:

```bash
cd <repo>/translation && \
  for sha in <sha8_a> <sha8_b>; do
    cp -r outputs/blocks/$sha /tmp/$sha.bak
  done && \
  ls -d /tmp/*.bak | head
```

Print the backup paths so the user (and future-you) can roll back instantly.

### Step 3 — Dry-run classification

```bash
cd <repo>/translation && \
  .venv/bin/python scripts/apply_reviewer_feedback.py \
    --xlsx <audit.xlsx> --dry-run
```

Report the summary block verbatim (approve / override / approved_with_alt / skip_retranslate / skip_note_only / skip_unchanged counts). Confirm with the user via `AskUserQuestion` that the counts look right before applying — the user knows the expected scale better than you do.

### Step 4 — Apply

After confirmation, run without `--dry-run`:

```bash
cd <repo>/translation && \
  .venv/bin/python scripts/apply_reviewer_feedback.py \
    --xlsx <audit.xlsx>
```

Capture stdout. Report: before/after status counts (the importer prints these as `meta <sha8>: {...}`), and how many rows landed (`applied N`).

### Step 5 — Surface skip_note_only rows

Reviewer left a comment but no correction. These need human judgment.

```bash
cd <repo>/translation && \
  .venv/bin/python ~/.claude/skills/apply-reviewer-audit/note_only_report.py \
    <audit.xlsx>
```

The script emits JSON with `rows[i].glossary_suggestions` pre-filled from `glossaries/glossary_ADVANCE_v1.json` (best-effort substring match against the reviewer's note, the judge rationale, and the fr/de text).

For **each** note-only row, present to the user:
- `file_sha8` + `block_id` + `status`
- FR text (truncated to 400 chars)
- DE text (truncated to 400 chars)
- Reviewer note (verbatim)
- Judge verdict + rationale (if present)
- QC summary (if present)
- The glossary suggestions (top 1–3 most relevant)

Then ask via `AskUserQuestion`:
- **Surgical fix** — apply a specific FR→DE replacement deterministically. If glossary suggestions are unambiguous (single canonical mapping in the note), pre-fill the find/replace pair from the suggestion.
- **Gemini retranslate** — surface this option but require explicit consent. If chosen, run `scripts/retranslate.py --file <sha8> --block-ids <bid>` with an env-set feedback hint. Confirm cost (1 LLM call per block).
- **Skip** — leave it for a later pass.

Apply surgical fixes by writing a small inline Python block via the BlockStore API (see `tools/block_store.py`). Stamp `provenance.note=reviewer_override`, `provenance.override_source=<short_tag>`, add a `history` entry with `previous_de`, `correction`, and the reviewer note. Mirror `scripts/apply_cog_recurring_sentence.py` for the stamping convention.

After landing surgical fixes, call `BlockStore.update_meta(sha8)` for each touched sha8.

### Step 6 — Address any remaining flagged blocks (optional, ask first)

Run a quick directory scan to see if any blocks are still `status=flagged` or `status=rejected` outside the reviewer's certified rows. Most often these are:
- Structural carriers (`""`, `"X"`, `"-"`, digits) — emit verbatim, ignore.
- Stale flags from pre-glossary-update QC — already glossary-canonical, just need `provenance.note=reviewer_approved`.

Show counts + dump non-carrier rows for the user. Ask whether to stamp stale-flag blocks as `reviewer_approved`. Don't bulk-stamp without confirmation.

### Step 7 — Confirm before regenerating downstream artifact

ALWAYS ask via `AskUserQuestion` before running the regen step. The block-store changes are committed at this point and rolling them back means restoring from `/tmp/<sha8>.bak`. The regen produces a user-visible deliverable that may need to ship.

For each impacted sha8, look up the regen recipe in `program_map.json`:

- **website** (e.g. `vitalite`, `serenite`):

  ```bash
  cd <repo>/translation && \
    cp de_translation_sources/website/<program>_german_translation_db.json \
       /tmp/<program>_german_translation_db.bak.json && \
    .venv/bin/python scripts/blocks_to_website_db.py <program>
  ```

  Then diff:

  ```bash
  .venv/bin/python -c "
  import json
  o = json.load(open('/tmp/<program>_german_translation_db.bak.json'))
  n = json.load(open('de_translation_sources/website/<program>_german_translation_db.json'))
  common = set(o) & set(n)
  diff = [k for k in common if o[k] != n[k]]
  print('changed:', len(diff), 'added:', len(set(n)-set(o)), 'removed:', len(set(o)-set(n)))
  "
  ```

- **manual** (COG_CB, CG): the regen path is via `tools/json_to_docx.py`. Discover the current rebuild helper in `translation/scripts/` (names rotate — look for `regen`, `rebuild`, `blocks_to_docx`, `assemble_docx`). If you can't find a clean wrapper, ask the user for the current script.

- **unknown sha8**: prompt the user for the regen command.

### Step 8 — Report

Summarise:
- Backup paths (so rollback is trivial).
- Apply counts (approve / override / approved_with_alt / skip_*).
- Note-only resolution per row (surgical / Gemini / skipped).
- Final block-store status counts per sha8.
- Regenerated artifact path + change count.
- Any leftover flagged / rejected blocks (with one-line reason if known: "structural carrier", "stale-flag", "unreviewed").

## File layout

```
~/.claude/skills/apply-reviewer-audit/
├── SKILL.md             # this file
├── program_map.json     # sha8 → program name + regen recipe
└── note_only_report.py  # surfaces skip_note_only rows + glossary suggestions
```

## Common pitfalls (observed across two prior runs)

- **Re-running on an already-applied XLSX**: `apply_reviewer_feedback.py` is idempotent — it skips rows where provenance is already `reviewer_override` / `reviewer_approved`. The summary will show `already_applied` counts. Don't be alarmed; just confirm the block-store state matches expectations.
- **Status counts vs on-disk recount disagreeing**: `_meta.json` can drift if multiple writers stamp the same sha8 without an intermediate `update_meta`. If the script's emit-time count differs from `meta['status_counts']`, trust the script (it walks disk).
- **"Innere Balance" vs "Gelassenheit"**: the Sérénité brand-name has a known glossary inconsistency. If you see one form being overwritten by the other, surface it to the user — do not silently normalize. See `glossaries/glossary_ADVANCE_v1.json` entry `Sérénité → Innere Balance` as the current canonical source.
- **`force_retranslate=TRUE` rows**: NOT handled by this skill. Those go through `scripts/import_xlsx_overrides.py`. Surface them to the user with a pointer.

## Cross-references

- `translation/scripts/apply_reviewer_feedback.py` — the underlying importer.
- `translation/scripts/blocks_to_website_db.py` — website regen.
- `translation/tools/block_store.py` — block-store API for surgical writes.
- `translation/glossaries/glossary_ADVANCE_v1.json` — canonical glossary.
- `translation/CLAUDE.md` — translation-pipeline-specific rules (especially "ALWAYS ASK FIRST").
- `translation/scripts/apply_cog_recurring_sentence.py` — reference for surgical-fix stamping pattern.
