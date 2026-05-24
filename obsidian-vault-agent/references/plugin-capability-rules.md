# Plugin Capability Rules

This guide maps common Obsidian plugins to operational constraints for vault editing.

## Rule Model

- `Protected syntax`: text structures that should not be rewritten by default.
- `Safe edits`: edits usually safe around this plugin.
- `High-risk edits`: edits likely to break plugin behavior and should require explicit user confirmation.

## Core Obsidian Features

### Daily Notes

- Protected syntax:
  - Date-title conventions used by templates and calendar workflows.
- Safe edits:
  - Content cleanup inside note body.
- High-risk edits:
  - Renaming date notes without updating references and periodic rules.

### Templates

- Protected syntax:
  - Placeholder and variable markers used by template engines.
- Safe edits:
  - Non-template prose sections.
- High-risk edits:
  - Rewriting variable placeholders or changing template file locations.

### Backlinks and Graph

- Protected syntax:
  - Wiki-link forms and heading anchors.
- Safe edits:
  - Prose around links.
- High-risk edits:
  - Bulk renames without link repair.

## Community Plugins (Observed Common Cases)

### `dataview`

- Protected syntax:
  - ```` ```dataview ```` and ```` ```dataviewjs ```` code fences.
  - Inline Dataview expressions.
- Safe edits:
  - Non-query prose.
  - Metadata additions that do not remove existing queried keys.
- High-risk edits:
  - Renaming or deleting frontmatter fields used in queries.

### `periodic-notes`

- Protected syntax:
  - Folder/date naming conventions for periodic notes.
- Safe edits:
  - Body text cleanup.
- High-risk edits:
  - Moving periodic note roots without settings update.

### `tag-wrangler`

- Protected syntax:
  - Existing tag taxonomy conventions.
- Safe edits:
  - Controlled tag normalization to a declared target taxonomy.
- High-risk edits:
  - Partial or inconsistent tag migration across vault.

### `obsidian-spaced-repetition`

- Protected syntax:
  - Flashcard and scheduling markers.
- Safe edits:
  - Non-card narrative text.
- High-risk edits:
  - Reflowing list structures containing flashcard markers.

### `pdf-plus`

- Protected syntax:
  - PDF links, annotation links, page references.
- Safe edits:
  - Prose around embedded references.
- High-risk edits:
  - Renaming or moving PDFs without repairing embeds.

### `obsidian-zotero-desktop-connector`

- Protected syntax:
  - Citation templates and imported bibliography blocks.
- Safe edits:
  - Non-citation sections.
- High-risk edits:
  - Editing generated citation anchors or IDs.

### `smart-connections`

- Protected syntax:
  - Plugin metadata blocks, semantic index markers.
- Safe edits:
  - Standard note content outside plugin markers.
- High-risk edits:
  - Deleting or rewriting sections explicitly used for embeddings/indexing.

## Generic Heuristics for Unknown Plugins

- Infer risk from plugin name and manifest description.
- If plugin text indicates `query`, `template`, `task`, `citation`, `calendar`, `pdf`, or `ai`, default to conservative behavior.
- When uncertain, preserve matching blocks and ask before rewriting.

## Execution Guardrails

- Always run capability scan before large transformations.
- Preserve unknown structured blocks by default.
- Prefer additive migrations over destructive rewrites.
- Report assumptions when plugin semantics are inferred, not confirmed.

