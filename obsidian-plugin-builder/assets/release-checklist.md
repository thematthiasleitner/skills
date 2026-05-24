# Obsidian Plugin Release Checklist

## Versioning

- [ ] `manifest.json` has target plugin version.
- [ ] `manifest.json.minAppVersion` is correct.
- [ ] `versions.json` includes target version mapped to minimum app version.

## Build and verification

- [ ] `npm ci` completed successfully.
- [ ] `npm run build` completed successfully.
- [ ] `main.js` reflects current source.
- [ ] Plugin loads in Obsidian without startup errors.
- [ ] Core acceptance checks pass.

## Repository and docs

- [ ] README reflects current capabilities and usage.
- [ ] Breaking changes are documented.
- [ ] LICENSE is present and valid.

## Release automation

- [ ] `.github/workflows/release.yml` exists and is valid.
- [ ] Workflow creates draft release on version tags.
- [ ] Release uploads `manifest.json`, `main.js`, and `styles.css` if present.

## Publish

- [ ] Release tag matches plugin version exactly.
- [ ] Draft release notes are reviewed.
- [ ] Draft release is published.
- [ ] Community submission/update step is complete.
