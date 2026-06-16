---
name: tag-batch-enrich
description: Enrich multiple ObsVault concept/tag files in one pass — pick the N stalest approved concepts (or a given list) and run the /tag-enrich workflow on each, with a confirmed plan first. Use when the user says "enrich N tags", "refresh my stale tags", "batch enrich", or after a semester's notes land and many concepts are outdated.
---

# /tag-batch-enrich <N | concept names | folder of sources>

Run the [/tag-enrich](../tag-enrich/SKILL.md) workflow over a batch. Read
[CONCEPT-FORMAT.md](../tag-create/CONCEPT-FORMAT.md) and the tag-enrich SKILL.md
first — this skill only adds batch selection, confirmation, and reporting on top.

## Selecting the batch

- **Number N** → the N stalest approved concepts: sort by the `*Synthesized
  YYYY-MM-DD*` date in each file (grep it; missing date = oldest). Default N = 10.
- **Names** → exactly those concepts.
- **Source folder** (e.g. a just-finished course) → concepts whose name appears in
  those notes; enrich the ones that exist, list non-existent ones as `/tag-create`
  candidates instead.
- Root canonicals (`0.Tags/*.md`) are excluded from batches — they are append-only
  and handled one at a time via `/tag-enrich`.

## Workflow

1. Refresh the index: `python3 .claude/scripts/tag-system/sync-concept-index.py --quiet`
2. Build the batch list and **present the plan before touching anything** (rule 7:
   >5 files always needs confirmation; show it even for smaller batches):

   | Concept | Last synthesized | Why selected |

3. On confirmation, enrich each file per the tag-enrich workflow (re-scan sources,
   update quotes, rewrite synthesis, preserve `wikilinks:` count + user section).
   Work file-by-file — never leave a file half-rewritten between steps. For large
   batches, parallel subagents are fine (one file per agent, no shared writes);
   give each agent the CONCEPT-FORMAT.md path and the hard rules.
4. Sync the index again.
5. **Report:** per concept — sources added/refreshed, one-line synthesis angle,
   anything flagged (dead source links, suspected duplicates, candidates for
   `/tag-audit` or the injector stoplist).

## Limits

- Cap a single run at ~25 concepts; suggest a follow-up run for the rest.
- If two batch members look like duplicates of each other, pause and tell the user
  instead of enriching both.
