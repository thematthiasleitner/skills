# Evolution log — vault-wikilink-toolkit

## 2026-05-24 — Skill created

Initial creation. Derived from these recurring vault-weaver tasks:

- **Strip subfolder-prefix wikilinks** (`[[0.Tags/approved/X]]` → `[[X]]`):
  the migration left ~4000 of these; the in-plugin command works but the
  toolkit lets the same operation run against any vault / any prefix.
- **Strip wikilinks not in approved/**: the strict disk-based scrub that
  required a clarifying AskUserQuestion. The `find-orphans` + `--scope`
  combination covers it.
- **Strip wikilinks to rejected slugs**: replaces the bespoke
  `scrubRejectedSlugs` for cross-plugin / one-off cleanup.

**Dry-run-by-default contract is hard-locked.** `--apply` requires
explicit flag AND user must see preview first. This is the lesson from
the destructive-shortcut anti-pattern: any cleanup that touches "lots of
files" must show what it will do before doing it.
