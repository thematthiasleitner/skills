---
name: obsidian-plugin-deploy
description: Build a custom Obsidian plugin in the ObsVault_Dev workspace and rsync the compiled artifacts to the production ObsVault — preserving `data.json` and `index.json`. **Medium-risk (overwrites prod plugin files; user settings are at risk if the exclude list is wrong) — DO propose via AskUserQuestion when the user has just finished editing plugin code OR says "deploy / ship / sync / install / push to prod", but NEVER silently invoke. Explicit user consent required.** Codifies the build → rsync → confirm dance that has tripped up sessions where files were overwritten or vaults fell out of sync.
tools: Bash, Read, AskUserQuestion
---

# Obsidian Plugin Deploy Skill

You build the named plugin in `ObsVault_Dev/.obsidian/plugins/<plugin>/` and
rsync the compiled artifacts to `ObsVault/.obsidian/plugins/<plugin>/`,
preserving `data.json` (user settings) and any plugin-owned cache files
(e.g. `index.json` for vault-weaver).

**This skill overwrites files in the production vault — medium-risk.**

## Discovery vs invocation

- ✅ **DO surface this skill via `AskUserQuestion`** whenever the user has
  finished editing files under `.obsidian/plugins/<plugin>/src/**` and has
  not yet deployed, OR they say "deploy / ship / sync / install / push to
  prod / try it in the real vault". State which plugin would be deployed
  and which files changed so they can decide informed.
- ❌ **NEVER silently invoke.** Production vault overwrites are not free —
  if the exclude list is wrong, user settings vanish.
- ✅ **If the user types `/obsidian-plugin-deploy <plugin>`** or explicitly
  approves the AskUserQuestion proposal, that IS explicit consent.

The AskUserQuestion proposal should:
- Name the plugin
- Show 1-line summary of changed files since last deploy (or "all files,
  no prior deploy detected")
- Note side effects ("overwrites `<prod>/.obsidian/plugins/<plugin>/`,
  preserves `data.json` + `index.json`")
- Offer alternative ("build only, don't deploy yet" / "deploy without
  rebuilding")

## When NOT to propose

- The plugin folder has no `package.json` → not a custom plugin, refuse.
- Production vault path doesn't exist on this machine → ask before
  inventing one.
- TypeScript errors are present → propose fixing first.

---

## Workflow

### Step 0: Gate via AskUserQuestion

If the user hasn't explicitly typed `/obsidian-plugin-deploy`, propose it.
Always include alternatives. Use the question header "Deploy?".

### Step 1: Detect plugin + verify paths

```bash
PLUGIN_DIR="/Users/matthias/ObsVault_Dev/.obsidian/plugins/<plugin>"
PROD_DIR="/Users/matthias/ObsVault/.obsidian/plugins/<plugin>"
test -f "$PLUGIN_DIR/package.json" || { echo "Not a custom plugin"; exit 1; }
test -d "$PROD_DIR" || echo "WARN: prod dir does not exist — will be created"
```

### Step 2: Build

```bash
cd "$PLUGIN_DIR" && npm run build
```

If build fails, surface the error and STOP. Do not rsync a stale `main.js`.

### Step 3: Rsync with explicit excludes

**The exclude list is sacred.** Per CLAUDE.md "Lessons" → "User-modifiable
persistence is sacred during deploys."

```bash
rsync -av \
  --exclude='data.json' \
  --exclude='index.json' \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='src' \
  --exclude='*.map' \
  "$PLUGIN_DIR/" "$PROD_DIR/"
```

For plugins beyond vault-weaver, the only universal excludes are
`data.json` + `node_modules` + `.git`. `index.json` is vault-weaver-specific
— check the plugin's source for other JSON caches it writes and add them.

### Step 4: Confirm

After rsync, diff what's in prod vs dev:

```bash
diff -q "$PLUGIN_DIR/main.js" "$PROD_DIR/main.js" && echo "main.js synced"
diff -q "$PLUGIN_DIR/manifest.json" "$PROD_DIR/manifest.json" && echo "manifest synced"
test -f "$PROD_DIR/data.json" && echo "data.json preserved" || echo "WARN: no data.json in prod"
```

Report:
- Plugin name + version (from manifest.json)
- Files copied (filter rsync -v output)
- `data.json` preservation status
- Suggestion: "reload <plugin> in Obsidian to apply"

---

## Safety invariants

- **Never overwrite `data.json`.** Always in --exclude.
- **Never overwrite plugin-owned caches** (vault-weaver's `index.json`,
  any other plugin's writeable JSON files). Inspect plugin source for
  what it writes via `app.vault.adapter.write()` before deploying.
- **Never use `--delete`** in rsync — would prune user-added files in prod.
- **Never `git push` as a deployment step.** Per CLAUDE.md. The deploy
  channel is rsync.
- **Refuse if working tree is dirty without confirmation.** The user might
  be mid-edit.

## On failure

- Build fails: surface the TypeScript / esbuild error verbatim. Don't try
  to fix without consent.
- Rsync fails: report the path that errored. Common cause is the prod
  vault being on an external drive that's unmounted.

---

## Self-evolution

If this skill is invoked and one of the following happens, propose an
adjustment to the user (one-line proposal, await consent before editing
SKILL.md):

- User clarifies an exclude that should have been there ("don't overwrite
  X") → propose adding X to the universal exclude list.
- Build always succeeds but rsync always fails on the same path → propose
  fixing the prod path resolution.
- User invokes this 3+ times for the same plugin with the same flags →
  propose creating a plugin-specific wrapper or default.
- Skill is invoked but the user redirects ("no, just build" / "no, skip
  the diff") → propose splitting into two skills OR adding a flag.

On approval: edit SKILL.md AND append to [EVOLUTION.md](EVOLUTION.md) with
date + change + rationale.

## Composes with

- `/vault-weaver-health-check` — run after deploying vault-weaver to
  confirm the new build is behaving on prod data.
- `/vault-weaver-concept-trace` — debug a specific concept post-deploy if
  the user reports regression.
