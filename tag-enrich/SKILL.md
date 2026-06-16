---
name: tag-enrich
description: Re-synthesize an existing concept/tag file in ObsVault 0.Tags/ — re-scan the vault for notes mentioning it, refresh the synthesis and per-source quote summaries, preserve the user section. Use when the user says "enrich/update/refresh tag X", a tag is stale, or new notes mention an existing concept.
---

# /tag-enrich <concept name>

Refresh one existing concept file. Read
[~/.claude/skills/tag-create/CONCEPT-FORMAT.md](../tag-create/CONCEPT-FORMAT.md)
first — file template, frontmatter, and the non-negotiable vault rules live there.

## Workflow

1. **Locate the file** via `concept-index.json` (case-insensitive).
   - In `approved/` or `pending/` (VW format) → full enrich, steps 2–6.
   - Root canonical `0.Tags/<Name>.md` (LX format) → **append-only**: you may add new
     `### [[source|label]]` + `> [!quote]` sections under `## Vault sources`, above
     the `<!-- lexikon:user-section -->` sentinel. Never touch `LX_*` frontmatter,
     the Wikipedia abstract, or existing sections. Confirm with the user first.
   - In `rejected/` → ask; enriching a rejected concept means resurrecting it.
   - Not found → offer `/tag-create`.
2. **Capture what must survive.** Note the existing `wikilinks:` count (keep it), the
   user section below the sentinel (byte-for-byte), and `VW_lang`.
3. **Re-scan the vault** for notes mentioning the concept (grep name + inflections;
   exclude `0.Tags/`, `0.Templates/`, dot-folders; `0.Journal/` only on request).
   Diff against the sources already cited in the file.
4. **Update per-source sections:** add `### [[path|label]]` + `> [!quote]` for new
   substantive sources; refresh quotes whose source notes changed materially; keep
   still-accurate ones verbatim. If a cited note no longer exists, keep the section
   but flag it to the user — never silently drop content.
5. **Rewrite the synthesis** (1–4 paragraphs, conversational, analogies, wikilinks to
   other approved concepts) and set `*Synthesized <today>*`. If the file uses the
   legacy `## Source notes` + `> [!quote]-` shape, migrate it to `## Sources` +
   `### [[path|label]]` while preserving all quote content.
6. **Re-emit sentinel + user section unchanged**, then sync the index:
   `python3 .claude/scripts/tag-system/sync-concept-index.py --quiet`

## Edit discipline

- Use targeted edits where possible; a full rewrite of the managed section is fine,
  but the file must never be emptied as an intermediate state (vault rule 3).
- Any `<!--SR:...-->` comment found anywhere stays byte-identical.
- Report what changed: sources added/refreshed, synthesis angle, anything flagged.
