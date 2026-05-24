# Implementation Guardrails

Apply these rules while building plugin code.

## Required manifest standards

- Keep required fields present: `id`, `name`, `version`, `minAppVersion`, `description`, `author`, `isDesktopOnly`.
- Keep `version` in semantic version format `x.y.z`.
- Keep plugin `id` free of `obsidian`.
- Keep plugin folder name equal to `manifest.id` for reliable local behavior.

## Lifecycle and cleanup

- Initialize resources in `onload()`.
- Release resources on unload.
- Register event listeners with `registerEvent()` so cleanup is automatic.
- Use `registerInterval()` for timers so timers are cleaned up automatically.

## Commands

- Use `checkCallback` / `editorCheckCallback` when command availability is conditional.
- Avoid default hotkeys for community plugins.
- Do not include plugin ID in command IDs.

## Settings and persistence

- Load settings on startup using `loadData()`.
- Persist setting changes with `saveData()`.
- Treat nested setting objects carefully; shallow copy defaults can cause shared references.

## Views

- Register views using `registerView()`.
- Access existing view instances using `getLeavesOfType()`; do not keep global references to view instances.

## Vault operations

- Use `cachedRead()` for read-only display flows.
- Use `read()` for read-modify-write flows.
- Prefer `Vault.process()` over manual `read()` + `modify()` for atomic modifications.
- Use Vault APIs over Adapter APIs unless Adapter-only behavior is strictly required.

## Mobile and platform constraints

- If plugin relies on Node.js/Electron APIs, set `isDesktopOnly` to `true`.
- Avoid unsupported browser features on mobile (for example lookbehind regex on older iOS versions).

## UI and security

- Prefer sentence case in UI labels.
- Avoid `innerHTML`, `outerHTML`, and `insertAdjacentHTML` with user-controlled values.
- Prefer Obsidian DOM helpers (`createEl`, `createDiv`, `createSpan`) and standard DOM APIs.
