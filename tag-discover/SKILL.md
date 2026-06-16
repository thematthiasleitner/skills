---
name: tag-discover
description: Scan an ObsVault note or folder and propose new concepts worth adding to the 0.Tags/ system, scored and deduplicated against the ~3,000 existing concepts. Use when the user says "what concepts are in this note/folder", "discover tags", "what should I tag here", or after finishing a batch of new course notes.
---

# /tag-discover [note | folder] 

Propose new concepts from vault content. Proposal only — creates nothing until the
user picks. Format and rules: [CONCEPT-FORMAT.md](../tag-create/CONCEPT-FORMAT.md).

## Scope

- No argument → ask which note/folder, or use the currently open file if obvious.
- Single note → deep read, propose 3–10 concepts.
- Folder → read the notes (sample if >20 files; say so), propose 10–25 concepts.
- Vault-wide runs are expensive: confirm first and work folder-by-folder.
- Never scan `0.Journal/` unless explicitly asked (personal content).

## Workflow

1. **Load the existing concept set** from
   `.claude/scripts/tag-system/concept-index.json` (refresh it first with
   `python3 .claude/scripts/tag-system/sync-concept-index.py --quiet`). Every
   proposal must be checked against ALL four statuses — never re-propose a
   rejected concept without flagging that it was previously rejected.
2. **Read the target content** and extract candidate concepts. Good candidates score
   on the Vault Weaver criteria: recurrence (appears in several places), bridging
   (connects course topics), explanatory power, utility for future traversal,
   underdevelopment (the vault keeps mentioning it without a home), intrigue.
3. **Filter hard.** Drop: existing concepts (any status), generic words ("time",
   "process"), one-off proper nouns, anything only mentioned in passing.
4. **Present a table** sorted by score:

   | # | Concept | Lang | Why it earns a tag | Source notes | Suggested status |

   `Suggested status`: approved (clearly recurring) or pending (worth review).
5. **Wait for the user's picks**, then run the `/tag-create` workflow for each picked
   concept. >5 creations = bulk: show the plan and confirm before writing (rule 7).

## Output discipline

Proposals are cheap, files are not — when unsure whether something deserves a tag,
propose it with an honest "why" and let the user decide. Never silently create.
