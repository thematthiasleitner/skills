---
name: reference-flashcards
description: Sync curated thesis reference PDFs into the Obsidian vault and create thesis-defense flashcards for any not yet covered. For each article in Thesis/References, checks whether it already has a note in the ACTIVE vault References tree and whether that note already has flashcards; if not, drafts a reference note (citation + summary + cards grounded in the PDF) and runs flashcard-audit to curate, dedupe, and register them. Use when the user adds articles to Thesis/References, asks to update the vault References folder, or wants thesis/defense flashcards built from their reference library.
tools: Read, Edit, Write, Bash, Grep, Glob, Agent, AskUserQuestion, TodoWrite, Skill
---

# Reference Flashcards

Turn the curated reference library (`Thesis/References/`, organized in topic
subfolders and tracked by `INVENTORY.md`) into vault reference notes with
flashcards that help **write and defend the master's thesis**. Composes with
**`/flashcard-audit`** (which only *curates* existing cards — it cannot create
them, so this skill drafts the cards first).

## Paths (this workspace)

| | Path |
|---|---|
| Source PDFs | `…/RA NEAD/Thesis/References/<NN_topic>/*.pdf` |
| Active vault notes | `~/ObsVault/1.Projects/RA MSc NEAD/References/<NN_topic>/` |
| Archive (backup — IGNORED for presence checks) | `…/References/archive/` |
| Canonical card index | `~/ObsVault/.flashcard-audit/canonical-index.json` |

"Already in the vault" = a matching note in the **active** tree only. `archive/`
is an untouched backup and never counts as present.

## Workflow

### 1. Plan (deterministic, zero tokens)
```bash
python3 ~/.claude/skills/reference-flashcards/scan.py            # all present PDFs
python3 ~/.claude/skills/reference-flashcards/scan.py --article aitken
```
Emits JSON: per article `{topic, pdf, author, year, note_exists, n_cards, action, target_note}`.
`action` ∈ `create` (no note) · `add_cards` (note, no cards) · `skip` (note + cards).
Only `create`/`add_cards` need work.

### 2. Draft cards from each PDF (one subagent per article, in parallel)
Give each agent the `pdf` path and have it **read the actual PDF** (never invent
numbers — see [[feedback_citation_verification]]). It returns: full citation,
a 2–3 sentence summary, and 6–10 flashcards following the card spec below.
Batch the `create`/`add_cards` articles across parallel `Agent` calls.

### 3. Write the note (mirror the topic subfolder)
`create` → write `target_note`. `add_cards` → append a `## Flashcards` section to
the existing note (never rewrite existing prose or drop `<!--SR:…-->` history).
Use the note template below.

### 4. Curate with flashcard-audit
Invoke `/flashcard-audit folder <vault References path>` (or `file <path>` per
note). It rewrites keepers conversationally, retires weak/duplicate cards, and
registers survivors in the canonical index. Honor its dry-run/approval gate.

### 5. Report
Table: article × {present / created / cards added / skipped}, new index size.

## Card spec — write to defend the thesis

Each article's cards should arm the four things a committee probes. Aim to cover:

1. **Core claim** — the one finding the thesis leans on (with the real stat/effect).
2. **Method & why it matters** — the technique and what it buys (and its limit).
3. **Link to the thesis argument** — how this supports the V1→auditory /
   deep-layer-omission / emotional-voice story; what it does and doesn't license.
4. **Defense Q&A** — the awkward question a juror would ask, and the crisp answer
   (confound, alternative interpretation, generalization gap, sample size).

Style (matches `/flashcard-audit`): conversational, lead with *why it matters*,
1–3 sentence answers, analogies welcome, link concepts with `[[wikilinks]]`, no
author-year in the question. Real numbers must come from the PDF, not memory.

## Note template

```md
---
tags: [reference, fc/thesis]
authors: <Author, Author>
year: <YYYY>
doi: <doi or ISBN>
topic: <NN_topic>
source_pdf: "<absolute path to Thesis/References PDF>"
---
# <First-author et al.> (<year>) — <short title>

**Citation:** <full reference, mirrors Thesis/08_bibliography.md>

## Summary
<2–3 sentences: what they did, what they found, why it matters to the thesis.>

## Flashcards
<multiline `?` cards for concepts; `::` for quick facts. Example:>

Why does deep-layer activity during omission count as *prediction* rather than leftover sensory signal?
?
Because feedforward input enters layer 4 — with no stimulus, layer 4 stays quiet, so signal in layers 5/6 can only be top-down [[feedback]]. That anatomical asymmetry is what lets [[Aitken et al.]] read deep-layer activity as a prediction.
```

## Safety

- Idempotent: re-running skips articles that already have cards (`action: skip`).
- Never touch `archive/`. Never delete note prose or lose SR scheduling data.
- flashcard-audit stays dry-run-by-default; surface its table before applying.
- Books/abstracts without a usable PDF (status ❌/⚠️ in `INVENTORY.md`) are out of
  scope until a PDF is present.

## Composes with
- `/flashcard-audit` — curates + dedupes the cards this skill drafts.
- `INVENTORY.md` in `Thesis/References/` — the source-of-truth article list.
