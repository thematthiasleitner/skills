---
name: flashcard-audit
description: Audit flashcards in Obsidian vault notes — classify as keep/improve/retire, deduplicate across files, rewrite keepers in conversational tone with analogies. Uses a persistent canonical index to prevent cross-file duplicates. Dry-run by default. Invoke when the user wants to clean up, curate, or audit flashcards.
tools: Read, Edit, Write, Bash, Grep, Glob, Agent, AskUserQuestion, TodoWrite
---

# Flashcard Audit Skill

Curate the flashcard pool in `/Users/matthias/ObsVault` by classifying
every card as **keep**, **improve**, or **retire** — then rewriting keepers
in conversational tone and deactivating retirees. Uses a persistent
**canonical index** to detect and eliminate duplicates across files.

## Target state

**500-800 active cards** across the entire vault, down from ~7,400.
Every surviving card must pass at least one of these criteria:

1. **Transferable mental model** — an idea applicable across domains
2. **Conversation fuel** — surprising enough to retell at dinner
3. **Vocabulary you'd use** — fills a gap in active expression (FR/DE/EN)
4. **Principle that changes behavior** — shapes decisions in relationships, leadership, or judgment

Cards that fail all four get retired. No exceptions for academic prestige
or sunk cost.

> **Deck exception — `fc/thesis`** (added 2026-06-16; see [EVOLUTION.md](EVOLUTION.md)).
> Cards tagged `fc/thesis` (built by the `reference-flashcards` skill from the
> MSc reference library) follow a DIFFERENT keep-rule: keep a card if it helps
> the user *write or defend the thesis* (precise finding/stat, method rationale,
> or a juror Q&A). Do NOT apply RETIRE-NARROW ("too academic") here — precision
> is the point. Only retire `fc/thesis` cards that are true cross-file
> duplicates or broken/placeholder. They are time-boxed to the defense.

## Flashcard syntax reference

The vault uses the **Obsidian Spaced Repetition** plugin (v1.15.2):

| Type | Separator | Example |
|------|-----------|---------|
| Single-line | `::` | `front :: back` |
| Reversed single-line | `:::` | `back ::: front` |
| Multiline | `?` (on its own line) | Question `\n` `?` `\n` Answer |
| Reversed multiline | `??` (on its own line) | Answer `\n` `??` `\n` Question |

Scheduling data is inline: `<!--SR:!YYYY-MM-DD,interval,ease-->`

**Important**: `::` inside wikilinks (`[[tag::value]]`), URLs, or code
blocks is NOT a flashcard separator. Only match `::` that appears as the
primary structural separator of a line (with content on both sides).

## Canonical index

Persistent file at `/Users/matthias/ObsVault/.flashcard-audit/canonical-index.json`.

```json
{
  "version": 1,
  "target_pool_size": 700,
  "insights": [
    {
      "id": "relative-deprivation",
      "summary": "Tensions from comparative disadvantage, not absolute deprivation",
      "source_file": "3.Archive/MSc ISRI/S05_ISRI_TIS-TAC_P1.md",
      "source_line": 50,
      "tag": "fc/insight",
      "status": "approved"
    }
  ],
  "retired_count": 0,
  "last_audit": null
}
```

**Before classifying any card**, check the index for semantic duplicates.
If the same insight already has a canonical card elsewhere, retire the
duplicate — even if it's well-written. The canonical version wins.

If the new card is BETTER than the existing canonical, replace the
canonical pointer (and retire the old one on the next pass of that file).

## Operating modes

### `/flashcard-audit file <path>`
Audit a single markdown file. Extract all cards, classify each, present
a summary table, await approval, then apply changes.

### `/flashcard-audit folder <path>`
Audit all markdown files in a folder (recursive). Process file-by-file,
updating the canonical index as you go. Present a per-file summary.

### `/flashcard-audit status`
Report vault-wide stats: total active cards, canonical index size,
estimated daily review load, cards by tag, files not yet audited.

### `/flashcard-audit search <query>`
Search the canonical index for an insight. Useful before creating new
cards to check for duplicates.

---

## Workflow for auditing a file

### Step 1: Read the file and extract all cards

Parse the file and identify every flashcard by its separator. For each
card, extract:
- The question (front)
- The answer (back)
- The separator type (::, :::, ?, ??)
- The SR scheduling comment if present
- The line numbers it spans

### Step 2: Classify each card

For each card, evaluate against the 4 criteria. Also check the canonical
index for semantic duplicates. Assign one of:

| Verdict | Meaning |
|---------|---------|
| **KEEP** | Passes criteria, no duplicate in index. Will be rewritten. |
| **IMPROVE** | Good insight but card needs rewriting to pass. |
| **RETIRE-DUPLICATE** | Same insight already in canonical index. |
| **RETIRE-NARROW** | Too academic, too specific, no real-life utility. |
| **RETIRE-INCOMPLETE** | Draft, placeholder, broken, or image-only with no insight. |

### Step 3: Present the audit table

Show a summary table to the user:

```
## Audit: <filename>
Cards found: N | Keep: X | Improve: Y | Retire: Z

| # | Line | Verdict | Card summary (first 60 chars) | Reason |
|---|------|---------|-------------------------------|--------|
| 1 | 50   | KEEP    | Relative deprivation — tens... | Mental model |
| 2 | 120  | RETIRE  | Minimal group conditions...    | Duplicate of #8 in index |
...

### Proposed rewrites for KEEP/IMPROVE cards:
[Show the rewritten card text for each keeper]
```

### Step 4: Await user approval

Use AskUserQuestion: "Apply these changes? You can also override
individual verdicts (e.g., 'keep #3, retire #7')."

### Step 5: Apply changes

**For RETIRE cards** — deactivate by removing the separator and SR comment:
- Multiline (`?` / `??`): Delete the separator line. Remove `<!--SR:...-->`.
  The question and answer text stay as prose in the note.
- Single-line (`::` / `:::`): Replace separator with ` — ` (em-dash).
  Remove `<!--SR:...-->`. Content stays readable.

**For KEEP/IMPROVE cards** — rewrite:
- Replace question and answer text with the conversational rewrite
- **Preserve** the `<!--SR:...-->` comment if the core insight is unchanged
  (keeps scheduling history). Reset it (delete the comment) only if the
  card fundamentally changed meaning.
- Use whichever language feels most natural for the insight:
  - English for universal concepts and mental models
  - French for French-specific vocabulary or expressions
  - German for German-specific vocabulary
- Add analogies and visualisations where they help
- Use wikilinks to connect to existing vault concepts where natural

**For all changes**: Update the canonical index with new entries for kept
cards and increment `retired_count`.

### Step 6: Report

After applying, show:
- Cards kept / improved / retired in this file
- New canonical index size
- Estimated total active cards remaining in vault
- Next suggested file to audit (if doing folder/vault mode)

---

## Rewrite style guide

When rewriting a kept card:

1. **Conversational tone** — write as if explaining to a smart friend,
   not a textbook. Drop academic jargon unless it IS the point.

2. **Lead with the insight** — the question should frame WHY this matters,
   not "According to X (year), what..."

3. **Analogies** — ground abstract concepts in everyday experience.
   "Think of it like..." / "It's the same dynamic as..."

4. **Brevity** — answers should be 1-3 sentences. If you need more, the
   card should probably be split.

5. **Wikilinks** — link key concepts to existing vault notes, but don't
   over-link. 1-3 links per card max.

6. **No author-year citations in questions** — the card is about the
   insight, not who discovered it. Attribute in the answer if the person
   is part of the story (e.g., Tajfel's biography).

7. **Prefer `?` for conceptual cards, `::` for quick-fire facts/vocab.**

### Before → After example

**Before** (academic):
```
Selon la théorie de la comparaison sociale de Festinger, quel est
l'objectif fondamental de la comparaison au-delà de la simple
évaluation hiérarchique des compétences ?
?
L'objectif principal est la valorisation du soi, qui consiste à
s'attribuer un niveau de valeur personnelle satisfaisant...
```

**After** (conversational):
```
Why do we really compare ourselves to others — is it just to know where we rank?
?
Not mainly. We compare to establish our own worth. Ranking is a side effect — the real drive is to feel valuable. Think of how checking someone else's salary doesn't just inform you, it changes how you feel about yours. That shift in self-worth is the engine, not the scoreboard.
<!--SR:!2026-03-05,107,315-->
```

---

## Safety invariants

- **Dry-run by default.** Never apply changes without showing the audit
  table and getting explicit approval.
- **Never delete note content.** Retiring a card means removing the
  separator and SR comment, NOT deleting the prose.
- **Never lose SR scheduling data for kept cards.** If a card is kept
  and the insight is the same, preserve the `<!--SR:...-->` comment.
- **Canonical index is append-only during an audit.** Don't remove
  entries during an audit — only add new ones or update pointers.
- **Back up awareness.** Before large batch audits (>50 cards), suggest
  the user commits or stashes their vault state.

## Self-evolution

Propose adjustments when:

- The user consistently overrides a verdict pattern (e.g., always keeps
  vocabulary cards I'd retire) → update the criteria weighting.
- The target pool size (700) proves too high or too low → adjust.
- A new card purpose emerges that doesn't fit the 3 tags → propose a
  new tag.
- The rewrite style misses the user's tone → update the style guide.

On approval: edit SKILL.md AND append to [EVOLUTION.md](EVOLUTION.md).

## Batch pipeline (for vault-wide audits)

For auditing the full vault efficiently, use the batch pipeline instead
of the interactive file-by-file mode. This separates AI judgment from
mechanical work and can run with **Sonnet** to save tokens.

### Pipeline files

All in `/Users/matthias/.claude/skills/flashcard-audit/`:

| File | Purpose |
|------|---------|
| `extract_cards.py` | Extract all cards from vault → `extracted-cards.json` |
| `prepare_batches.py` | Auto-retire flagged cards, chunk rest into batches |
| `classify_prompt.md` | System prompt for Sonnet classification |
| `rewrite_prompt.md` | System prompt for Sonnet rewriting |
| `apply_changes.py` | Apply verdicts + rewrites to vault files |

### Pipeline steps

**Step 1: Extract** (zero tokens)
```bash
python3 ~/.claude/skills/flashcard-audit/extract_cards.py
```
Output: `.flashcard-audit/extracted-cards.json`

**Step 2: Auto-retire + prepare batches** (zero tokens)
```bash
python3 ~/.claude/skills/flashcard-audit/prepare_batches.py --retire-flagged
```
Flags `--retire-vocab` and `--retire-file "3.Archive/Italien/*"` available
for bulk decisions. Output: `.flashcard-audit/batches/batch_NNN.json`

**Step 3: Classify batches** (Sonnet — moderate tokens)

For each batch file, read `classify_prompt.md` as system instructions,
then feed the batch JSON and collect JSONL output. Append results to
`.flashcard-audit/classifications.jsonl`.

In Claude Code with Sonnet:
```
Read classify_prompt.md, then classify the cards in batch_000.json.
Append your verdicts to classifications.jsonl.
```

Or run `/flashcard-audit classify` which processes batches sequentially.

**Step 4: Rewrite keepers** (Sonnet — moderate tokens)

Extract cards classified as `keep` from `classifications.jsonl`, feed
them with `rewrite_prompt.md`, collect rewrites into `rewrites.jsonl`.

**Step 5: Review** (human)

Spot-check `classifications.jsonl` and `rewrites.jsonl`. Override by
editing the files directly (they're plain JSONL).

**Step 6: Apply** (zero tokens)
```bash
python3 ~/.claude/skills/flashcard-audit/apply_changes.py      # dry run
python3 ~/.claude/skills/flashcard-audit/apply_changes.py --apply  # commit
```

### Running with Sonnet

Sonnet handles classification reliably because:
- The criteria are explicit and calibrated with examples
- Each batch is self-contained (no conversation history needed)
- Output is structured JSONL (easy to validate)

**Do NOT use Haiku** for classification — it tends to be too permissive
and misses the "90% retirement" target. Haiku can be used for mechanical
tasks (running scripts, applying changes).

### Resumability

The pipeline is crash-safe:
- `classifications.jsonl` is append-only — rerunning skips already-done cards
- `prepare_batches.py` skips already-classified cards when creating batches
- `apply_changes.py` is idempotent on the same input

## Composes with

- **flashcard-forge** (planned) — creates new cards that pass the quality
  gate and register in the canonical index from day one.
- **flashcard-garden** (planned) — periodic maintenance: find leeches,
  zombies, orphans.
- `/vault-wikilink-toolkit` — clean up wikilinks in cards that reference
  deleted or moved notes.
