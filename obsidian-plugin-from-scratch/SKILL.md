---
name: obsidian-plugin-from-scratch
description: Operationalize and implement Obsidian plugins from idea to working codebase, without handling publishing. Use when users ask to create a new Obsidian plugin, define MVP scope, scaffold plugin architecture, or implement plugin features (commands, settings, views, vault operations, lifecycle/events) according to official Obsidian plugin documentation.
---

# Obsidian Plugin From Scratch

Build an Obsidian plugin from zero to a production-ready codebase.
Do not handle marketplace submission or release publishing here; use `$obsidian-plugin-release-github` for that phase.

## Load these resources first

- Read `references/docs-map.md` for canonical documentation pages.
- Read `references/implementation-guardrails.md` before coding.
- Use `assets/plugin-spec-template.md` to operationalize the idea.
- Use `assets/implementation-checklist.md` before handing off to release.

## Workflow

1. Operationalize the idea

- Convert the request into `Problem`, `Target user`, `MVP`, `vNext`, `Out of scope`, and `Acceptance checks`.
- Ensure acceptance checks are observable behaviors.
- Decide early whether plugin is desktop-only (`isDesktopOnly: true`) or cross-platform.

2. Scaffold safely and correctly

- Use a dedicated development vault, not the user's main vault.
- Start from the official sample plugin structure.
- Confirm `manifest.json` required fields are valid and `id` matches the plugin folder name.
- Establish build/dev loop (`npm install`, `npm run dev`) and plugin reload workflow.

3. Implement feature slices

- Implement one acceptance check at a time.
- Use appropriate API patterns:
  - `addCommand` / `checkCallback` / `editorCallback` for commands.
  - `PluginSettingTab`, `loadData`, and `saveData` for settings.
  - `registerView` + `getLeavesOfType` for custom views.
  - `registerEvent` and `registerInterval` for lifecycle-safe listeners/timers.
  - `Vault.process` for atomic background file edits.
- Avoid global `app` usage and avoid unsafe DOM APIs (`innerHTML`, `outerHTML`, `insertAdjacentHTML`) with user input.

4. Validate engineering quality before release handoff

- Verify plugin loads and unloads cleanly.
- Verify no persistent side effects after `onunload`.
- Verify settings persistence and migration behavior.
- Verify desktop/mobile expectations match `isDesktopOnly`.
- Run through `assets/implementation-checklist.md`.

## Hard constraints

- Always prefer official Obsidian docs over assumptions.
- Never include plugin ID inside command IDs (Obsidian prefixes automatically).
- Remove sample plugin placeholder names and sample-only code before handoff.
- Keep console output clean in default operation (errors only unless debugging).

## Deliverables

- Completed plugin spec based on `assets/plugin-spec-template.md`.
- Working plugin code with validated manifest metadata.
- Implementation checklist with explicit pass/fail notes.
