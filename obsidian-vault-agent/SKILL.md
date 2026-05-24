---
name: obsidian-vault-agent
description: Execute safe Obsidian vault content manipulation with awareness of Obsidian core features and installed community plugins. Use when asked to reorganize notes/folders, normalize frontmatter or tags, fix wiki links and embeds, run batch markdown transformations, consolidate templates/daily-note structures, or perform plugin-aware refactors based on `.obsidian` configuration.
---

# Obsidian Vault Agent

Operationalize and execute Obsidian vault content manipulation tasks safely, at scale, and with plugin-aware behavior.

## Load these resources first

1. Run the capability scanner to detect active core/community plugins and manifest metadata:

```bash
scripts/scan_obsidian_capabilities.py --vault <vault-path> --format markdown
```

2. Read `references/content-manipulation-playbook.md`.
3. Read `references/plugin-capability-rules.md` and focus on plugins present in the scan output.

## Workflow

1. Define scope and constraints

- Confirm target folders and file types.
- Confirm protected paths that must never be read or modified.
- Confirm whether operation is in-place, additive, or migration style.

2. Build a vault capability map

- Inspect `.obsidian/core-plugins.json` and `.obsidian/community-plugins.json` via the scanner.
- Use plugin `manifest.json` metadata to infer affected syntax and behaviors.
- Flag plugin-dependent syntax before editing any note.

3. Plan transformation passes

- Split work into deterministic passes: structure, metadata, links, content blocks.
- Prefer idempotent transformations.
- Define validation checks before edits.

4. Execute edits safely

- Edit only text-based note files (`.md`) unless explicitly asked otherwise.
- Preserve YAML frontmatter validity.
- Preserve plugin-specific query/code blocks unless task explicitly targets them.
- Apply atomic, reviewable changes.

5. Validate and summarize

- Re-scan and verify target patterns were updated.
- Verify no unresolved wiki-link syntax was introduced.
- Report what changed, where, and what remains manual.

## Hard constraints

- Never modify protected paths provided by user or vault policy.
- Never assume plugin semantics without checking installed plugin IDs and manifests.
- Never break markdown structure (frontmatter fences, code fences, callout fences, headings hierarchy) during batch edits.
- Never rewrite attachment binaries.

## Typical tasks handled well

- Normalize frontmatter fields across notes.
- Standardize and deduplicate tags.
- Rename folders/notes and repair wiki-links.
- Convert inline conventions to structured frontmatter.
- Refactor repeated sections into templates.
- Reorganize project/area/archive folder hierarchies while preserving references.

## Deliverables

- Edited notes with plugin-safe transformations.
- Brief change log with counts and paths.
- Validation summary with detected risks or follow-up actions.
