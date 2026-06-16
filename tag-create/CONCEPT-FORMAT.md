# ObsVault concept-file format (shared reference for all /tag-* skills)

Vault: `/Users/matthias/ObsVault`. Concepts live in `0.Tags/`. Two formats coexist:

## 1. VW format — `0.Tags/{approved,pending,rejected}/*.md` (~2,900 files)

The format the /tag-* skills read and write. Template for a new or rewritten file:

```markdown
---
wikilinks: 0
VW_lang: en
VW_status: approved
VW_approved: true
VW_rejected: false
VW_concept_slug: my-concept
---

# My Concept

*Synthesized 2026-06-12*

[[Synthesis]] paragraphs: what this concept is across the whole vault, written in
a conversational tone with analogies, weaving in [[wikilinks]] to other approved
concepts. 1–4 paragraphs.

## Sources

### [[2.Areas/MSc Course/2026-01-15 Topic|2026-01-15 Topic]]

> [!quote]
> What this specific note says about the concept — 2–5 sentences, concrete.

<!-- vault-weaver:user-section -->
```

Field semantics:

- `VW_status` / `VW_approved` / `VW_rejected` triplets — always consistent:
  - approved: `approved` / `true` / `false` (file in `approved/`)
  - pending: `pending` / `false` / `false` (file in `pending/`)
  - rejected: `rejected` / `false` / `true` (file in `rejected/`)
- `VW_lang`: `en` / `fr` / `de` — language the concept file is written in. Match the
  dominant language of the source notes.
- `VW_concept_slug`: lowercase, non-alphanumerics collapsed to `-` (slugify of name).
- `wikilinks`: legacy Vault Weaver counter of vault-wide inbound links for this
  concept. Do NOT invent a value: keep the existing number when enriching, use `0`
  for new files. It is a cache, staleness is fine.
- `*Synthesized YYYY-MM-DD*` line: update to today whenever the synthesis is rewritten.
- Concept name = filename (without `.md`). Avoid `[ ] # ^ | : \ / * ? " < >` in names.

Older files may instead have `## Source notes` with `> [!quote]- Title` foldable
callouts wrapping the source link — that is a valid legacy shape. When enriching,
rewrite to the `## Sources` + `### [[path|label]]` shape above.

## 2. Lexikon format — the ~105 root files `0.Tags/*.md` (canonical, hand-curated)

`LX_*` frontmatter, `cssclasses: [lexikon]`, a `> [!abstract] Wikipedia — [Title](url)`
callout, `## Vault sources` with `### [[path|label]]` + `> [!quote]` sections, sentinel
`<!-- lexikon:user-section -->`.

**Skills never rewrite these.** The only permitted automated change is appending a new
`### [[source|label]]` + quote section under `## Vault sources` (above the sentinel),
and only when the user explicitly asks. Never touch `LX_*` frontmatter or the abstract.

## Hard rules (vault CLAUDE.md, non-negotiable)

1. Never delete a concept file. Rejecting = move to `0.Tags/rejected/` + flip frontmatter.
2. Everything at or below `<!-- vault-weaver:user-section -->` or
   `<!-- lexikon:user-section -->` is user-owned: preserve byte-for-byte, always
   re-emit the sentinel when rewriting a file.
3. Never modify `<!--SR:...-->` spaced-repetition comments anywhere.
4. Section titles use `#` heading syntax, never bold-as-title.
5. Any operation touching >5 files: present a dry-run plan and get confirmation first.
6. Moving a file between `0.Tags/` subfolders is safe for `[[name]]` links (Obsidian
   resolves by basename), but never rename a concept file casually.

## Tooling (deterministic layer, no LLM)

Scripts in `/Users/matthias/ObsVault/.claude/scripts/tag-system/`:

- `sync-concept-index.py` — rebuild `concept-index.json` (name/path/status/lang of all
  concepts). **Run after any create/move/approve/reject** so the index stays current.
- `inject-wikilinks.py TARGETS...` — inject `[[links]]` for approved+canonical concepts
  into notes. Dry-run by default, `--apply` to write. `stoplist.txt` holds names that
  must never auto-link.
- `strip-wikilinks.py NAMES... | --rejected` — unwrap `[[links]]` for rejected concepts.
  Dry-run by default.

Check `concept-index.json` (or the four folders, case-insensitively) before creating
any concept — duplicates across approved/pending/rejected/canonical are forbidden.
