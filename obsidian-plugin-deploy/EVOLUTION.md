# Evolution log — obsidian-plugin-deploy

Adjustments to this skill, with date + change + rationale. Append-only.

## 2026-05-24 — Skill created

Initial creation. Derived from repeated patterns in vault-weaver development
sessions where:
- `data.json` was at risk of being overwritten by rsync
- `index.json` (vault-weaver's cache) needed to be preserved
- Plugin compiled successfully but wasn't synced to prod, causing
  user-visible bugs that "should have been fixed"

**Universal excludes locked in:** `data.json`, `node_modules`, `.git`,
`src`, `*.map`.
**Plugin-specific exclude noted for vault-weaver:** `index.json`.
