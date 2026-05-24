---
name: vault-weaver-health-check
description: Diagnose the Vault Weaver plugin's lifecycle state — compare the on-disk concept files (approved/pending/rejected subfolders) against the in-memory index, analyse the activity log for anomalies (ping-pongs, repeated errors, lifecycle imbalances), and surface mismatches before they become user-visible bugs. **Low-risk (read-only diagnostic) — propose freely via AskUserQuestion whenever the user reports weird vault-weaver behaviour ("concepts moving on their own", "rejected count is wrong", "index disagrees with files", "scrub did nothing"), OR after a /obsidian-plugin-deploy of vault-weaver, OR after a maintenance command that touched many files.** Never mutates state — only reads.
tools: Bash, Read, AskUserQuestion
---

# Vault Weaver Health Check

Read-only diagnostic for the Vault Weaver plugin. Compares:
- On-disk concept files in `0.Tags/{approved,pending,rejected}/`
- The in-memory `index.json` cache
- The activity log emitted by `runMaintenance()` / `logActivity()` / `updateActivity()`

Surfaces:
- Mismatches between disk state and index (file in approved/ but index
  says rejected, or vice versa)
- Concepts in the index that have no file on disk (orphan index entry)
- Concept files with no index entry (orphan file)
- Ping-pong patterns in the activity log (same slug moved 2+ times in
  rapid succession)
- Lifecycle imbalances (e.g. 90% rejected — likely over-eager noise filter)
- Repeated error log lines (the same error 3+ times = systemic issue)

## Discovery vs invocation

- ✅ **DO surface via `AskUserQuestion`** when:
  - The user reports a vault-weaver bug ("X is wrong / weird / not working")
  - The user just deployed vault-weaver via `/obsidian-plugin-deploy`
  - The user just ran a bulk maintenance command (scrub, migrate, sort)
  - The user asks "is vault-weaver behaving?" / "what's the state?"
- ❌ Don't auto-invoke. The user may be mid-task.
- ✅ Explicit `/vault-weaver-health-check` is explicit consent.

The AskUserQuestion proposal should:
- Note this is **read-only** (so consent threshold is low)
- Offer the user a choice of scope: "full" (index ↔ disk + log) vs
  "log-only" (faster, if files weren't recently touched)
- Always offer "skip" as an alternative

## When NOT to propose

- The vault is not the ObsVault_Dev dev vault (no symlinks expected to
  match `index.json` schema).
- The user is in the middle of editing plugin code — propose deploying
  first instead, then run this after.

---

## Workflow

### Step 0: Gate via AskUserQuestion (unless `/vault-weaver-health-check`)

### Step 1: Locate inputs

```bash
VAULT="/Users/matthias/ObsVault_Dev"   # or /Users/matthias/ObsVault for prod check
INDEX="$VAULT/.obsidian/plugins/vault-weaver/index.json"
CONCEPTS="$VAULT/0.Tags"
LOG="$VAULT/.obsidian/plugins/vault-weaver/activity.log"   # if exists
```

Confirm each input exists. If `index.json` is missing → plugin hasn't run
yet or was wiped; report and stop.

### Step 2: Audit index vs disk

```bash
python3 ~/.claude/skills/vault-weaver-health-check/audit_index_vs_disk.py \
  --vault "$VAULT" \
  --format human
```

Output sections:
- Counts: approved/pending/rejected on disk + index totals
- **Mismatches** — disk says X, index says Y (the bug class that caused
  the 120-rejected-only-12-files incident)
- **Orphan index entries** — index has slug, no file exists
- **Orphan files** — file exists, no index entry (often legacy files
  pre-migration)

### Step 3: Analyse activity log (if present)

```bash
python3 ~/.claude/skills/vault-weaver-health-check/analyze_activity_log.py \
  --log "$LOG" \
  --since "24h"
```

Output sections:
- **Ping-pongs**: same slug moved between subfolders within < 5s, 2+
  times. The signature of the live-handler-loop bug that caused infinite
  movement.
- **Error clusters**: same error message 3+ times.
- **Lifecycle imbalance**: ratio of pending/approved/rejected vs healthy
  baseline (~70/20/10).
- **Tick performance**: median + p95 tick duration; flag if any tick
  > 10s (UI-freeze territory).

### Step 4: Synthesise findings

Render a single report in this shape:

```
Vault Weaver health — <vault path> — <date>

Disk:    approved=X  pending=Y  rejected=Z   total=W
Index:   approved=X  pending=Y  rejected=Z   total=W
Status:  ✅ in sync   OR   ⚠ N mismatches (see below)

Activity log (last 24h):
  Ticks: N (median 230ms, p95 1.4s, max 3.2s) — healthy
  Ping-pongs: 0
  Errors: 0

[Mismatches section, if any]
[Orphans section, if any]
[Recommendations section]
```

If mismatches found, surface them with file paths + the action the user
could take (typically: open settings → Maintenance → "Reconcile from
frontmatter"). Do not run any fix automatically.

---

## Safety invariants

- **Read-only.** Never `vault.modify`, never `rm`, never edit
  `index.json`, never touch concept files.
- **Reports paths, not contents.** Don't dump concept file bodies into
  the report.
- **If `index.json` is locked / mid-write**, retry once after 500ms.
  If still locked, report "index is being written — try again in a moment"
  and stop.

---

## Self-evolution

Propose adjustments (await user consent before editing) when:

- The user runs this 3+ times in a session for the same vault → propose
  caching the vault path as a default.
- A finding pattern recurs (same kind of mismatch in different sessions)
  → propose adding a named rule to the Python helper so the report
  highlights it specifically with a known-cause hint.
- The "healthy baseline" ratios prove wrong for the user's actual usage
  → propose updating the baseline thresholds.
- The user repeatedly asks "but what does this mean?" about a finding →
  propose adding a "what this means" / "what to do" line per finding.

On approval: edit SKILL.md / the Python helpers AND append to
[EVOLUTION.md](EVOLUTION.md) with date + change + rationale.

## Composes with

- `/obsidian-plugin-deploy` — run this AFTER deploying vault-weaver to
  confirm new build hasn't regressed.
- `/vault-weaver-concept-trace` — drill into a single slug surfaced by
  this skill's mismatch report.
- `/vault-wikilink-toolkit` — if this skill reports orphan wikilinks,
  that's the cleanup tool.
