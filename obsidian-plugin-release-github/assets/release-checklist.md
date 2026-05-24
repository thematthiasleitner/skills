# Obsidian Plugin Release Checklist (GitHub)

## A. Metadata consistency

- [ ] `manifest.json.version` is the intended release version (`x.y.z`).
- [ ] Git tag equals `manifest.json.version` exactly (no `v` prefix).
- [ ] `manifest.json.minAppVersion` is correct for shipped features.
- [ ] `versions.json` compatibility map is updated when required.

## B. Build and artifacts

- [ ] Build succeeded and generated current `main.js`.
- [ ] Release includes required files as individual assets:
  - [ ] `main.js`
  - [ ] `manifest.json`
  - [ ] `styles.css` (if plugin uses styles)
- [ ] Required repository files exist at root:
  - [ ] `README.md`
  - [ ] `LICENSE`
  - [ ] `manifest.json`

## C. Workflow automation

- [ ] `.github/workflows/release.yml` is present and valid.
- [ ] GitHub Actions workflow permissions allow read/write for contents.
- [ ] Tag push creates a draft release with expected assets.

## D. Policy and submission quality gates

- [ ] Plugin complies with Developer policies.
- [ ] Plugin complies with Submission requirements for plugins.
- [ ] Plugin is self-reviewed against Plugin guidelines.
- [ ] Manifest `description` is concise and policy-aligned.
- [ ] `isDesktopOnly` is true when Node/Electron APIs are used.

## E. Initial submission only

- [ ] Entry added to `community-plugins.json` with matching `id`.
- [ ] PR opened to `obsidian-releases` using Community Plugin template.
- [ ] PR checklist items are completed.
- [ ] Review feedback is handled on the same PR.

## F. Update release only

- [ ] Existing users can update from GitHub release.
- [ ] Compatibility expectations for older Obsidian versions are documented.
- [ ] Release notes communicate user-visible changes and breaking behavior.
