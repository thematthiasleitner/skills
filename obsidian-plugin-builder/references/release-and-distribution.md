# Release And Distribution Workflow

Follow this sequence for predictable first releases and updates.

## First publication

1. Verify repository contains:
   - `manifest.json`
   - `versions.json`
   - built `main.js`
   - `styles.css` if plugin uses styles
2. Verify plugin `id` is stable and machine-safe (lowercase and hyphenated).
3. Build plugin and run smoke tests in Obsidian.
4. Tag a release version that matches `manifest.json.version`.
5. Publish GitHub release with plugin assets attached.
6. Submit plugin to community index using Obsidian release docs.

## Normal update release

1. Implement and test changes.
2. Update plugin version and minimum app support:
   - `python3 scripts/update_obsidian_versions.py --manifest manifest.json --versions versions.json --version <x.y.z> [--min-app-version <a.b.c>]`
3. Build so `main.js` matches source changes.
4. Commit versioned artifacts.
5. Push tag matching plugin version (for example `1.3.0`).
6. Publish the generated GitHub release draft.

## GitHub Actions expectations

- Trigger on tags.
- Install dependencies with `npm ci`.
- Build plugin before release creation.
- Create draft release and upload build assets.
- Use repository `GITHUB_TOKEN` and `gh` CLI in workflow runner.

Use `assets/workflows/release.yml` as baseline.

## Failure recovery

- If release asset is wrong, rebuild and re-upload assets before publishing.
- If tag version mismatches `manifest.json.version`, delete draft release/tag and recreate with aligned version.
- If `versions.json` missed the release version, patch it immediately and publish a corrective release.
