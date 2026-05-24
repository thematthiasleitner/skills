# Content Manipulation Playbook

Use this playbook for any Obsidian vault transformation task.

## 1. Inputs to Confirm Before Editing

- Vault root path.
- Include paths (folders or file globs to process).
- Exclude paths (folders that must never be read or modified).
- Operation mode:
  - In-place edit existing notes.
  - Additive output to new files.
  - Migration to new folder structure.
- Success criteria (what "done" means).

## 2. Safety Gates

- Do not touch excluded paths, even for discovery.
- Limit edits to text notes (`.md`) unless explicitly requested.
- Preserve frontmatter fences (`---`) and valid YAML syntax.
- Preserve fenced code blocks, callouts, and block IDs (`^block-id`) unless requested.
- Preserve plugin syntax that may have runtime meaning.

## 3. Standard Execution Flow

1. Discovery
- Map candidate files with `rg --files`.
- Detect syntax patterns to protect (queries, templates, citations, tasks).

2. Planning
- Break work into deterministic passes:
  - Structure pass (folders, filenames, headings).
  - Metadata pass (frontmatter keys, tags, aliases).
  - Link pass (wiki links, embeds, anchors).
  - Content pass (text normalization, section templates).

3. Dry checks
- Compute counts before edits (files matched, patterns matched).
- Identify high-risk files (large files, many links, many code blocks).

4. Edit
- Apply atomic edits.
- Keep transformations idempotent where possible.

5. Validate
- Re-run pattern checks.
- Re-check unresolved links and malformed frontmatter.

6. Summarize
- Provide changed file counts, key paths, and residual manual follow-ups.

## 4. Plugin-Aware Protection Rules

- Do not rewrite these blocks unless task explicitly targets them:
  - Dataview code fences: ```` ```dataview ... ``` ````.
  - Dataview inline fields: `` `= expression` ``.
  - Templater blocks and template placeholders.
  - Tasks plugin syntax in list items.
  - Zotero citation templates and auto-generated bibliography sections.
  - Smart Connections or AI annotation markers.

## 5. Link and Path Handling

- Prefer preserving wiki-link style already used by the vault.
- Update both standard links and embeds:
  - `[[Note]]`
  - `[[Note#Heading]]`
  - `![[Attachment.pdf]]`
- When renaming notes, update display aliases if present:
  - `[[Old Name|Label]]`
- Keep anchors and heading references intact.

## 6. Frontmatter Normalization Pattern

- Keep key casing consistent across notes.
- Use stable field ordering when normalizing.
- Preserve unknown keys; do not drop metadata silently.
- Use list type consistently for multivalue fields (for example tags, aliases).

## 7. Common Deliverables

- A concise change log:
  - What changed.
  - How many files changed.
  - Which folders were affected.
- A risk log:
  - Files skipped.
  - Patterns intentionally untouched.
  - Items requiring manual review.

## 8. "Done" Checklist

- Target edits completed.
- Protected paths untouched.
- Plugin-sensitive syntax preserved unless requested.
- No broken frontmatter fences.
- No obvious malformed wiki-link syntax introduced.

