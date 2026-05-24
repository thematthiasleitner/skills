---
name: obsidian-plugin-release-github
description: Release, publish, and update Obsidian plugins using GitHub releases and official submission workflow. Use when users ask to upload a plugin, configure GitHub release automation, submit an initial plugin to the community directory, or ship updates while keeping manifest and versions metadata correct.
---

# Obsidian Plugin Release Github

Handle the publishing lifecycle for Obsidian plugins, including first submission and all later updates.
Do not build core plugin features here; use `$obsidian-plugin-from-scratch` for implementation.

## Load these resources first

- Read `references/release-docs-map.md` for canonical docs.
- Read `references/release-reliability-rules.md` before preparing any release.
- Use `assets/release-checklist.md` before publishing.
- Use `assets/workflows/release.yml` as the baseline GitHub Actions workflow.
- Run `scripts/update_obsidian_versions.py` to keep `manifest.json` and `versions.json` aligned.

## Workflow

1. Classify release type

- `Initial submission`: plugin not yet listed in `community-plugins.json`.
- `Update release`: plugin already listed.

2. Prepare release metadata and artifacts

- Ensure root files exist: `README.md`, `LICENSE`, `manifest.json`, built `main.js`, optional `styles.css`.
- Use semantic version format `x.y.z`.
- Ensure release tag exactly matches `manifest.json.version` (no `v` prefix).
- Update versions metadata:
  - `python3 scripts/update_obsidian_versions.py --manifest manifest.json --versions versions.json --version <x.y.z> [--min-app-version <a.b.c>] [--record-every-release]`

3. Build and draft GitHub release

- Build plugin artifacts (`npm install` + `npm run build` or project-equivalent).
- Configure `.github/workflows/release.yml` from asset template.
- Ensure repository Actions permission is set to read/write for releases.
- Push version tag and verify draft release contains required binary assets.

4. Publish and submit (initial only)

- Add plugin entry to `obsidianmd/obsidian-releases` `community-plugins.json`.
- Open PR with the community plugin template and complete all checklist items.
- Do not open a second PR for review feedback; update release and continue on same PR thread.

5. Publish and maintain (updates)

- Ship new tagged releases with required assets.
- Keep compatibility mapping in `versions.json` accurate when minimum app version changes.
- Maintain changelog/release notes for each published version.

## Hard constraints

- Attach required release assets as individual files, not only source archives.
- Keep `id` in submission JSON identical to `manifest.json.id`.
- Respect Developer policies and submission requirements before publishing.
- Avoid release metadata mismatches; version/tag mismatch is a blocker.

## Deliverables

- Release checklist with explicit pass/fail status.
- Verified tag + release alignment report.
- For initial publish: ready-to-submit community plugin PR payload.
- For updates: published GitHub release and compatibility metadata update.
