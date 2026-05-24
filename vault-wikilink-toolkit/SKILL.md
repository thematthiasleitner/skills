---
name: vault-wikilink-toolkit
description: Scan, preview, and rewrite/strip Obsidian `[[wikilinks]]` across a vault using configurable patterns — with a dry-run-by-default contract. Solves the recurring problem of cleaning up orphan wikilinks, stripping subfolder prefixes like `[[0.Tags/approved/X]]` → `[[X]]`, removing wikilinks whose target file no longer exists, or removing links to a deny-list of slugs. **Medium-risk (mutates user notes when --apply is passed) — DO propose via AskUserQuestion whenever the user describes a vault-wide wikilink cleanup, OR after rejecting a batch of concepts, OR after vault-weaver migration moves files. NEVER silently invoke. NEVER apply without showing a dry-run preview first.**
tools: Bash, Read, AskUserQuestion
---

# Vault Wikilink Toolkit

Generic wikilink scanner / rewriter for any Obsidian vault. Built on top of
[wikilink_scanner.py](wikilink_scanner.py), which exposes operations:

| Operation | What it does |
|---|---|
| `find-orphans` | List `[[X]]` whose target file does not exist anywhere in the vault. |
| `strip-prefix` | Rewrite `[[<prefix>/X]]` → `[[X]]`, e.g. `[[0.Tags/approved/X]]` → `[[X]]`. |
| `strip-slugs` | Remove `[[X]]` matching a deny-list (e.g. rejected vault-weaver concepts). |
| `find-broken` | Like `find-orphans` but limits to a specific folder scope. |

**Default mode is `--dry-run`.** Mutation requires `--apply` AND explicit
user consent after seeing the preview.

## Discovery vs invocation

- ✅ **DO surface via `AskUserQuestion`** when the user says any of:
  - "clean up broken / orphan / dead / dangling wikilinks"
  - "strip the `0.Tags/...` prefix from my links"
  - "remove links to rejected concepts"
  - "I just rejected N concepts, can we scrub the references?"
  - "the migration left old paths in my notes"
- ❌ **NEVER apply without preview consent.** Even after the user agrees
  to "run it", show the dry-run output, count + sample, then ask
  "apply to N files?" before mutating.
- ✅ Explicit `/vault-wikilink-toolkit <operation>` is consent to RUN
  the operation in dry-run; apply still needs a second confirmation.

The AskUserQuestion proposal should:
- State which operation would run
- Show estimated scope ("scans entire vault" / "scans 0.Tags only")
- Promise dry-run first
- Offer alternative ("skip" or "narrow the scope")

## When NOT to propose

- The user asked about a SINGLE file's links → just read it and report;
  this skill is for vault-wide ops.
- The vault has uncommitted changes the user is mid-edit on — propose
  committing or stashing first.

---

## Workflow

### Step 0: Gate via AskUserQuestion (unless invoked via `/vault-wikilink-toolkit`)

### Step 1: Dry-run

```bash
python3 ~/.claude/skills/vault-wikilink-toolkit/wikilink_scanner.py \
  --vault "$VAULT" \
  --op <operation> \
  [--scope "0.Tags/**/*.md"] \
  [--prefix "0.Tags/approved/"] \
  [--slugs-file rejected_slugs.txt] \
  --dry-run
```

Output:
```
=== DRY RUN ===
Op: strip-prefix
Scope: vault-wide
Would modify N files (M wikilinks total)

Sample edits (first 10):
  daily/2024-12-03.md  [[0.Tags/approved/anchor]] → [[anchor]]
  ...
```

### Step 2: Show preview to user + AskUserQuestion to apply

The preview is a summary, not a full diff dump. Always include:
- Total files affected
- Total wikilinks modified
- First 10 sample edits with file paths
- One question: **"Apply these changes to N files?"** Options: Apply / Skip
  / Narrow scope.

### Step 3: Apply (only on explicit consent)

```bash
python3 ~/.claude/skills/vault-wikilink-toolkit/wikilink_scanner.py \
  --vault "$VAULT" \
  --op <operation> \
  ... \
  --apply
```

Reports total files written + total edits applied.

### Step 4: Verify (optional)

Re-run the dry-run after apply. Should report 0 remaining matches. If not,
surface what's left and stop.

---

## Safety invariants

- **`--dry-run` is the default.** `--apply` must be explicitly typed AND
  user must have seen the preview.
- **Never modify outside the vault root** — refuse paths that escape via
  `..`.
- **Always write atomically** — write to `path.md.tmp`, then rename
  on top of the original. Never partial writes.
- **Yield-in-Python is implicit** (no UI thread to freeze), but the
  scanner still streams files and never loads the whole vault into memory.
- **Backup-by-git, not by copy.** Tell the user to `git status` / commit
  before applying. The script does not create `.bak` files.
- **One operation per invocation.** Don't chain operations in a single
  call; chaining hides intent.

---

## Self-evolution

Propose adjustments (await consent before editing SKILL.md) when:

- The user invokes the same operation 3+ times with the same `--scope`
  → propose making that scope the default for that operation.
- A new pattern recurs that isn't covered by an existing operation
  → propose adding a new `--op`.
- The dry-run preview is too verbose / too sparse for the user's taste
  → propose changing the sample size.
- The user repeatedly skips the preview ("just apply it") → DO NOT
  silently remove the preview step. Surface that you've noticed the
  pattern and ask whether the safeguard should be relaxed for specific
  operations only.

On approval: edit SKILL.md / scanner AND append to
[EVOLUTION.md](EVOLUTION.md).

## Composes with

- `/vault-weaver-health-check` — produces lists of orphan slugs / rejected
  slugs that feed this toolkit's `--slugs-file`.
- `/vault-weaver-concept-trace` — drill into a single slug before deciding
  whether to strip it vault-wide.
- `/obsidian-plugin-deploy` — after deploying vault-weaver with a new
  scrub command, prefer the in-plugin command if available; this skill is
  the cross-plugin / agnostic alternative.
