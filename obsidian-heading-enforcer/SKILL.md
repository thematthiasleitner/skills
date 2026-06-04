---
name: obsidian-heading-enforcer
description: Detect and fix bold text misused as section titles in Obsidian Markdown files, converting them to proper headings. Use when user asks to audit, lint, or fix heading formatting, or when editing vault notes that may contain bold-as-title patterns.
---

# Obsidian Heading Enforcer

Replace bold text used as titles/section labels with proper Markdown headings (`#`, `##`, etc.).

## Why

Bold text (`**Like This**`) used as a standalone section title breaks the document outline, prevents Obsidian's table-of-contents and heading-based features from working, and is inconsistent with Markdown semantics. Headings should always use `#` syntax.

## Detection pattern

A line qualifies as "bold-as-title" when **all** of the following are true:

1. The line consists entirely of bold text (possibly with a trailing colon or period): `**Some Title**`, `**Some Title:**`
2. It is followed by content (not another heading) — i.e., it introduces a section
3. It is **not** inside a callout, blockquote, table cell, or code block
4. It is **not** inline emphasis within a sentence (e.g., "The **critical current** Ic is...")

## Workflow

### Single-file audit (default)

1. Read the target file.
2. Scan for lines matching the detection pattern.
3. For each match, determine the correct heading level from context:
   - Look at the nearest preceding heading and use one level deeper.
   - If no preceding heading, default to `##`.
4. Present a preview of proposed changes (old line → new line) before editing.
5. On user approval, apply edits.

### Batch audit

1. Glob for `*.md` files in the target directory.
2. Run the single-file scan on each.
3. Report a summary table: `| File | Line | Current | Proposed |`.
4. Edit only after user approval.

## Edge cases

- **Numbered bold steps** like `**1. Title**` → convert to heading and keep the number: `#### 1. Title`
- **Bold text inside callouts** (`> **Title**`) → leave alone; callouts have their own formatting rules
- **Bold + colon introducing a list** (`**Key details:**`) on its own line → convert to heading without the colon
- **Bold inside a paragraph** → never convert; it's inline emphasis, not a title

## Hard constraints

- Never change heading levels of existing `#` headings.
- Never edit inside code fences or YAML frontmatter.
- Always preserve the document's existing heading hierarchy — infer the correct level, don't guess.
- Always show the user a diff preview before applying changes.
