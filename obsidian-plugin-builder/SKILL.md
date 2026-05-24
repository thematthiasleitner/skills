---
name: obsidian-plugin-builder
description: Legacy orchestration wrapper for full-lifecycle Obsidian plugin requests that explicitly need both implementation and release in one run. Use when users ask for a single combined flow; otherwise prefer the split skills obsidian-plugin-from-scratch and obsidian-plugin-release-github.
---

# Obsidian Plugin Builder

Prefer specialized skills.

## Routing

- For idea operationalization and coding:
  - Use `$obsidian-plugin-from-scratch`.
- For GitHub release automation, first upload, and updates:
  - Use `$obsidian-plugin-release-github`.

## Combined flow (only when explicitly needed)

1. Run `$obsidian-plugin-from-scratch` and produce a release-ready codebase.
2. Run `$obsidian-plugin-release-github` to publish and maintain releases.

Keep this skill lean and use the split skills as source-of-truth workflows.
