---
name: translate-doc
description: Translate a DOCX or PPTX from FR to DE using the existing ADVANCE translation pipeline (Gemini Flash + ADVANCE glossary). Codifies the env-var setup, the sample-before-full protocol, the progress-sidecar resume pattern, and the choice between tools/translate_docx_pipeline.py (DOCX) and scripts/translate_pptx.py (PPTX). Invoke when the user wants to translate a single Word or PowerPoint document FR→DE for the ADVANCE project. Does NOT handle batch translation jobs (those go through scripts/translate_folder.py) or block-store content (which uses translate_json.py against the block API).
---

# translate-doc

One-shot FR→DE translation of a single `.docx` or `.pptx` for the ADVANCE project. Wraps the two pipelines we already use (`tools/translate_docx_pipeline.py` and `scripts/translate_pptx.py`) with the boilerplate that always needs to go around them.

## When to invoke

- User asks "translate this Word document / slide deck to German" and points at a single file.
- Workflow follows a manual delivery (not a batch run, not block-store content).
- Examples from this session: `french_emails_language3.docx` (DOCX pipeline), the two facilitator-training PPTX decks (PPTX pipeline).

Do NOT invoke for:
- Block-store / website / manual content — that goes through the reviewer-audit flow + `apply-reviewer-audit` skill.
- Folder-scale batches — use `scripts/translate_folder.py` directly.
- Re-translation of a flagged block — use `scripts/retranslate.py`.

## Inputs

- `--input PATH` (required) — the `.docx` or `.pptx` source.
- `--output PATH` (optional) — defaults to the source filename with the `_de` suffix in the same directory.
- `--max-slides N` / `--max-blocks N` (optional) — sample mode: translate only the first N units. Per `feedback_sample_before_full_run.md`, always sample first if the doc is non-trivial.
- `--model NAME` (optional) — default `gemini-flash-latest`.
- `--glossary PATH` (optional) — default `translation/glossaries/glossary_ADVANCE_v1.json`.

## Workflow

### Step 1 — Detect file type and route

```bash
ext = Path(args.input).suffix.lower()
if ext == ".docx":
    # use tools/translate_docx_pipeline.py
elif ext == ".pptx":
    # use scripts/translate_pptx.py
else:
    fail with "unsupported extension"
```

### Step 2 — Set Gemini env vars

```bash
export LLM_PROVIDER=gemini
export LLM_MODEL=gemini-flash-latest
# GEMINI_API_KEY must already be in translation/.env
```

The user's hactar (LLM_BASE_URL) is only reachable on UNIGE VPN; Gemini is the default for off-VPN work.

### Step 3 — Sample-before-full (default protocol)

For files ≥ 30 paragraphs (DOCX) or ≥ 10 slides (PPTX): translate a small representative slice first, inspect the output, then run the full pass. Per `feedback_sample_before_full_run.md`:

```bash
# DOCX sample
python tools/translate_docx_pipeline.py \
  --input-file <input.docx> \
  --glossary glossaries/glossary_ADVANCE_v1.json \
  --model gemini-flash-latest \
  --max-blocks 10 \
  --target-lang de --source-lang fr

# PPTX sample
python scripts/translate_pptx.py \
  --input <input.pptx> --output /tmp/sample_de.pptx \
  --max-slides 3 --glossary glossaries/glossary_ADVANCE_v1.json
```

Inspect the sample (read paragraphs from output via python-docx / python-pptx), verify:
- Glossary terms render canonically (e.g. `engagement social → soziale Einbindung`, `Sérénité → Innere Balance`).
- Brand names are not declined (e.g. `GEISTIGE FRISCHE` stays caps-locked).
- Placeholders like `{name}`, `{login}`, `{APP_URL}` are preserved.
- Multi-language content (English/Italian) is correctly skipped (not re-translated).

Report sample output to the user. Confirm via AskUserQuestion before launching the full run.

### Step 4 — Full pass

```bash
# DOCX
LLM_PROVIDER=gemini LLM_MODEL=gemini-flash-latest \
  .venv/bin/python tools/translate_docx_pipeline.py \
    --input-file <input.docx> \
    --glossary glossaries/glossary_ADVANCE_v1.json \
    --model gemini-flash-latest \
    --target-lang de --source-lang fr

# PPTX
LLM_PROVIDER=gemini LLM_MODEL=gemini-flash-latest \
  .venv/bin/python scripts/translate_pptx.py \
    --input <input.pptx> \
    --output <output_de.pptx> \
    --glossary glossaries/glossary_ADVANCE_v1.json
```

Both pipelines write progress to a sidecar (PPTX: `<output>.progress.json`; DOCX: an intermediate `<input>_translated.json`). If the run is interrupted, rerunning the same command picks up where it left off — DO confirm this with the user before re-running on a non-empty sidecar (resume semantics may differ from intent).

Background long runs explicitly if expected to take more than ~2 minutes; you'll get a completion notification.

### Step 5 — Validate the output

For DOCX/PPTX: read a few paragraphs from the output (via python-docx / python-pptx) and visually confirm placeholders survived, glossary terms are canonical, no [r1]…[/r1] markers leaked into the user-visible text.

Report to the user:
- Output path + file size.
- Total paragraphs/slides translated, cached, skipped (the pipeline log surfaces these).
- Any failures (the pipeline log reports them by paragraph ID — copy the lines verbatim).

## Hard constraints

- **Always sample before full run** for non-trivial files. Per `feedback_sample_before_full_run.md`. If the user opts out, get explicit confirmation.
- **Respect the glossary.** Default glossary is `translation/glossaries/glossary_ADVANCE_v1.json`. Do not skip the `--glossary` arg.
- **Never auto-rename the source.** The output goes to a new file (`*_de.docx` / `*_de.pptx`). Never overwrite the FR original.
- **No silent provider switching.** If Gemini fails (quota, network) report to the user before falling back to anything else.
- **Resume semantics need confirmation.** If a `.progress.json` sidecar exists from a prior run, ASK before resuming — it may be stale.

## Common pitfalls (observed today)

- **Hactar VPN dependency**: the local LLM server (`LLM_BASE_URL=http://hactar...`) only works when on UNIGE VPN. For off-VPN runs, set `LLM_PROVIDER=gemini` explicitly.
- **Gemini caching disabled below threshold**: Gemini Flash's prompt cache has a ≥ 1024-token system prompt floor. Short translation prompts won't cache — that's a warning, not an error.
- **PPTX group shapes**: `scripts/translate_pptx.py` recursively descends into group shapes (`shape_type==6`). Verified working; just don't accidentally use a simpler iter-shapes helper for PPTX.
- **DOCX run markers**: paragraphs with multiple formatting runs use `<r1>...</r1>` markers in the LLM payload to preserve formatting. If they leak into final output, that's a bug — report and skip.
- **Gemini Flash daily quota**: 100 calls/day on the free tier (see `reference_gemini_tts_quota.md` for the TTS-equivalent number; chat may differ). Plan accordingly for large batches.

## File layout

```
~/.claude/skills/translate-doc/
└── SKILL.md
```

Pure orchestration skill — no helper script needed, since the underlying pipelines (`tools/translate_docx_pipeline.py`, `scripts/translate_pptx.py`) already encapsulate the heavy lifting. Future tightening could add a tiny `translate_doc.py` wrapper that handles the .docx/.pptx routing + env setup in one call.

## Cross-references

- Underlying pipelines:
  - `translation/tools/translate_docx_pipeline.py` — DOCX → JSON → translate → DOCX
  - `translation/scripts/translate_pptx.py` — PPTX → translate-in-place → PPTX
- Glossary skill: `/glossary <term>` to verify canonical mappings before/after translation.
- Block-store translation (DIFFERENT): `translation/tools/translate_json.py` (called by the audit flow, not this skill).
- Sample-first protocol: see `~/.claude/projects/<id>/memory/feedback_sample_before_full_run.md`.
