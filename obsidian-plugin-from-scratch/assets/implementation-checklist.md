# Obsidian Plugin Implementation Checklist

## Project setup

- [ ] Development happens in a dedicated test vault.
- [ ] Plugin folder name matches `manifest.id`.
- [ ] `npm install` and `npm run dev` complete successfully.

## Manifest quality

- [ ] Required manifest fields are present.
- [ ] `version` uses `x.y.z`.
- [ ] `id` is unique and does not contain `obsidian`.
- [ ] `isDesktopOnly` matches actual API usage.

## Feature correctness

- [ ] Commands work from command palette.
- [ ] Conditional commands use `checkCallback` or `editorCheckCallback` correctly.
- [ ] Settings load/persist correctly after app restart.
- [ ] Custom views open/reopen without duplication issues.

## Lifecycle hygiene

- [ ] `onload` initializes resources once.
- [ ] `onunload` leaves no stale listeners/timers/DOM artifacts.
- [ ] Registered events and intervals are cleanup-safe.

## Vault and data safety

- [ ] File edits use `Vault.process()` when atomicity matters.
- [ ] Active-editor edits use editor APIs when applicable.
- [ ] No unsafe path handling for user-provided paths.

## UI and policy alignment

- [ ] UI labels follow sentence case.
- [ ] No unsafe `innerHTML`/`outerHTML` usage with user content.
- [ ] Console logging is minimal in normal operation.
- [ ] Placeholder sample code/class names removed.

## Handoff readiness

- [ ] Acceptance checks in spec are all validated.
- [ ] Known limitations are documented.
- [ ] Codebase is ready for release workflow handoff.
