---
name: tag-audit
description: Review pending concepts in ObsVault 0.Tags/pending/ and batch approve or reject them with reasoning — moving files between status folders and keeping frontmatter consistent. Use when the user says "audit/review/triage my pending tags", "approve or reject pending concepts", or after /tag-discover has filled pending/.
---

# /tag-audit [N | concept names]

Triage `0.Tags/pending/` (≈200 files). Format, frontmatter triplets, and hard rules:
[CONCEPT-FORMAT.md](../tag-create/CONCEPT-FORMAT.md). **Never delete** — reject =
move to `rejected/` + flip frontmatter. **Moves are plain `mv`** between `0.Tags/`
subfolders; `[[name]]` links keep resolving because the basename is unchanged.

## Workflow

1. **Scope.** Default: review a batch of ~20 pending concepts (oldest first), or the
   N / the names the user gave. Refresh the index first:
   `python3 .claude/scripts/tag-system/sync-concept-index.py --quiet`
2. **Judge each concept** by reading its file and, where the file is thin, a quick
   grep for how often the vault actually mentions it:
   - **approve** — recurs across notes, bridges topics, the user would traverse to it
   - **reject** — generic word, one-off mention, duplicate-in-spirit of an existing
     concept (name the existing one), or noise from the old LLM pipeline
   - **defer** — genuinely unclear; stays pending, with a note on what would decide it
3. **Present the verdict table BEFORE changing anything** (rule 7 — this is always
   a bulk operation):

   | Concept | Verdict | Reasoning (one line) |

   Get explicit confirmation; the user may flip individual rows.
4. **Apply.** For each approval/rejection:
   - move the file: `pending/<X>.md` → `approved/<X>.md` or `rejected/<X>.md`
   - update the frontmatter triplet (`VW_status`/`VW_approved`/`VW_rejected`)
   - if a name collides with a file already in the target folder, stop and report —
     never overwrite.
5. **Sync the index** again, then report counts.
6. **Offer follow-ups, don't run them:** for rejected concepts whose links litter the
   vault → `strip-wikilinks.py --rejected` (dry-run); for newly approved ones that are
   thin → `/tag-enrich`.

## Judgement notes

- Approval is about traversal value for an MSc psychology/neuroscience vault, not
  encyclopedic completeness.
- When a pending concept duplicates a root canonical (`0.Tags/<X>.md`), reject the
  pending one and say it is covered by the canonical.
