# Obsidian Plugin Documentation Map

Use this file to locate canonical Obsidian guidance before implementing or releasing.

## Core development pages

- Create your first plugin:
  - https://docs.obsidian.md/Plugins/Getting%20started/Create%20your%20first%20plugin
- Build a plugin:
  - https://docs.obsidian.md/Plugins/Getting%20started/Build%20a%20plugin
- Manifest reference:
  - https://docs.obsidian.md/Reference/Manifest
- Versions reference:
  - https://docs.obsidian.md/Reference/Versions
- Submit your plugin:
  - https://docs.obsidian.md/Plugins/Releasing/Submit%20your%20plugin

## Releasing and policy pages

- Releasing section index:
  - https://docs.obsidian.md/Plugins/Releasing
- Release your plugin with GitHub Actions:
  - https://docs.obsidian.md/Plugins/Releasing/Release%20your%20plugin%20with%20GitHub%20Actions
- Submission requirements for plugins:
  - https://docs.obsidian.md/Plugins/Releasing/Submission%20requirements%20for%20plugins
- Plugin guidelines:
  - https://docs.obsidian.md/Plugins/Releasing/Plugin%20guidelines
- Beta testing plugins:
  - https://docs.obsidian.md/Plugins/Releasing/Beta%20testing%20plugins
- Developer policies:
  - https://docs.obsidian.md/Developer%20policies

## Fast interpretation

- Treat `manifest.json` as source of truth for current plugin metadata.
- Keep `versions.json` mapped as plugin version -> minimum app version.
- Publish GitHub release assets as `manifest.json`, `main.js`, and `styles.css` (if used).
- Expect initial community publication to require repository submission and review.

## URL fallback rule

If any direct URL above changes, open `https://docs.obsidian.md/Plugins/Releasing` and navigate by exact page title from this file.
