---
name: tag-create
description: Create a new concept/tag file in the ObsVault 0.Tags/ system — scan the vault for notes mentioning the concept, synthesize what it means across the vault, write per-source quote summaries in the Vault Weaver format, and file it under approved/ or pending/. Use when the user says "create a tag/concept for X", "add X to my tags", or accepts a /tag-discover proposal.
---

# /tag-create <concept name>

Create one concept file in the Vault Weaver format. Read
[CONCEPT-FORMAT.md](CONCEPT-FORMAT.md) first — it defines the exact file template,
frontmatter triplets, and the non-negotiable vault rules.

## Workflow

1. **Duplicate check.** Look up the name (case-insensitive, and its slug) in
   `.claude/scripts/tag-system/concept-index.json`. If it exists:
   - in `approved/` or root canonical → tell the user, suggest `/tag-enrich` instead.
   - in `pending/` → suggest `/tag-audit` to promote it.
   - in `rejected/` → it was consciously discarded; ask before resurrecting
     (resurrect = move the file back to `pending/`, never create a second file).
2. **Find sources.** Grep the vault for the concept name (and obvious inflections/
   translations — e.g. plural, FR/DE equivalents if the user works multilingually).
   Exclude `0.Tags/`, `0.Templates/`, dot-folders. Include `0.Journal/` only if the
   user asked. Rank hits by how substantively they discuss the concept.
3. **Read the best sources** (up to ~10 notes; skim, don't dump whole files into the
   reply). For each note that genuinely engages the concept, draft a 2–5 sentence
   `> [!quote]` summary of what *that note* says about it.
4. **Write the synthesis.** 1–4 paragraphs answering "what is this concept across my
   whole vault" — conversational tone, analogies welcome, wikilinks to other approved
   concepts woven in. Match `VW_lang` to the dominant source language.
5. **Place the file.**
   - ≥3 substantive sources and clearly useful → `0.Tags/approved/<Name>.md`
   - thinner evidence or uncertain value → `0.Tags/pending/<Name>.md`
   End the file with the `<!-- vault-weaver:user-section -->` sentinel.
6. **Sync the index:**
   `python3 .claude/scripts/tag-system/sync-concept-index.py --quiet`
7. **Offer (don't run unprompted) the injector** so the new concept gets linked:
   `python3 .claude/scripts/tag-system/inject-wikilinks.py <source notes> ` (dry-run).

## Quality bar

- A concept earns `approved/` when it recurs across notes, bridges topics, or the
  user will want to traverse to it. One-note mentions usually belong in `pending/`.
- Per-source quotes must say something specific ("this lecture ties X to dopamine
  prediction errors"), never generic filler ("this note discusses X").
- Never create files for trivially generic words (see `stoplist.txt` for the spirit).
