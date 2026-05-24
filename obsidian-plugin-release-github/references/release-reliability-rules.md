# Release Reliability Rules

Apply these rules before any publish action.

## Mandatory release assets and metadata

- GitHub release must include:
  - `main.js`
  - `manifest.json`
  - `styles.css` when present
- Release tag must match `manifest.json.version` exactly.
- Use semantic versioning format `x.y.z`.

## Repository readiness

- Keep `README.md` clear and usage-oriented.
- Keep `LICENSE` present and valid.
- Ensure plugin ID in `manifest.json` is stable and unique.
- Ensure community submission `id`, `name`, `author`, `description` match manifest metadata.

## versions.json policy

- `versions.json` maps plugin version -> minimum supported Obsidian app version.
- Update `versions.json` whenever `minAppVersion` changes.
- Keeping extra historical version mappings is acceptable but not required.

## Submission policy gates

- No code obfuscation.
- No client-side telemetry.
- No plugin self-update mechanism.
- Disclose in README when plugin requires accounts, payment, network access, external file access, server-side telemetry, or static ads in plugin UI.
- Set `isDesktopOnly` to `true` if plugin uses Node.js/Electron APIs.
- Keep description under 250 chars, plain language, no emoji/special characters, and ending with a period.

## Review-risk reduction

- Remove placeholder classes and sample plugin leftovers.
- Avoid default command hotkeys for public plugins.
- Keep console noise low in normal operation.
- Prefer safe DOM APIs and avoid HTML string injection with user content.
- Clean up resources on unload and avoid detaching leaves in `onunload`.
