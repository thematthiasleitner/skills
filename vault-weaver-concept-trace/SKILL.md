---
name: vault-weaver-concept-trace
description: Inspect a single Vault Weaver concept slug end-to-end — its on-disk file (path, subfolder, frontmatter, body length, callout count), its in-memory index entry (status, displayName, summaryUpdatedAt, perFileSummaries, signal score, duplicate flag), every vault wikilink that points to it, and the activity-log timeline of every move/edit it has been through. **Low-risk (read-only) — propose freely via AskUserQuestion when the user names a specific concept and asks "why is X behaving like this", "where did X go", "is X approved or rejected", "trace X for me", "what's the state of X".** Single-slug deep dive — complements /vault-weaver-health-check which scans the whole vault.
tools: Bash, Read, AskUserQuestion
---

# Vault Weaver Concept Trace

Single-slug inspector. The "why is yellow.md still in approved/" tool —
the one we needed in every debugging session but had to assemble by hand
every time.

Produces a one-page report with:
- **Disk**: file path, subfolder, full frontmatter, body length, callout
  count, last modified
- **Index**: status, displayName, summaryUpdatedAt, perFileSummaries count,
  needsFullSynthesis flag, signal score, duplicate-of, blocked status
- **Inbound wikilinks**: every `[[X]]` across the vault that points to
  this slug (file + line number + 1 line of context)
- **Timeline**: every activity-log event mentioning this slug (move,
  edit, error), most-recent-first
- **Diagnosis**: rule-based one-liner flagging known-bad combinations
  (e.g. "index says rejected, file in approved/, frontmatter says approved
  — classic misplacement bug; run /vault-weaver-health-check or open
  Maintenance → Reconcile from frontmatter")

## Discovery vs invocation

- ✅ **DO surface via `AskUserQuestion`** when the user names a specific
  concept and asks any "why / where / what state / trace" question about
  it, OR when `/vault-weaver-health-check` surfaces a mismatch and the
  user wants to investigate one of the offenders.
- ✅ This is read-only. Low consent threshold.
- ❌ Don't auto-invoke when the user is talking about concepts in
  general (use health-check instead).
- ✅ `/vault-weaver-concept-trace <slug>` is explicit consent.

The AskUserQuestion proposal should:
- Name the slug
- Note this is read-only
- Offer "skip" + "trace a different slug"

## When NOT to propose

- The user is asking about the plugin itself, not a specific concept.
- The slug is ambiguous (multiple candidates) — first ask which.

---

## Workflow

### Step 0: Gate via AskUserQuestion (unless `/vault-weaver-concept-trace <slug>`)

### Step 1: Resolve slug

The user may give a slug, a displayName, or a filename. Normalise:

```bash
python3 ~/.claude/skills/vault-weaver-concept-trace/trace_concept.py \
  --vault "$VAULT" \
  --query "$USER_INPUT"
```

If 0 matches: report and stop.
If >1 matches: list them and ask which.
If exactly 1: run the trace.

### Step 2: Render report

```bash
python3 ~/.claude/skills/vault-weaver-concept-trace/trace_concept.py \
  --vault "$VAULT" \
  --slug "$SLUG" \
  --format human
```

Output sections (always in this order):

```
== Concept: <displayName> (slug: <slug>) ==

Disk:
  Path: 0.Tags/approved/yellow.md
  Subfolder: approved   (last-modified: 2026-05-24T11:47:03Z)
  Frontmatter:
    VW_status: approved
    VW_approved: true
    VW_rejected: false
    VW_concept_slug: yellow
  Body: 1247 chars, 12 callouts

Index:
  Status: approved
  displayName: yellow
  summaryUpdatedAt: 2026-05-23T17:22:11Z
  perFileSummaries: 12 entries
  needsFullSynthesis: false
  signalScore: 0.78
  duplicate-of: (none)

Inbound wikilinks (4):
  daily/2024-12-03.md:14   "...the [[yellow]] one in the bin..."
  ...

Timeline (last 10 events):
  2026-05-24T11:47:03Z  moved pending → approved  (reconcile-from-frontmatter)
  2026-05-24T11:46:51Z  user flipped VW_approved=true
  ...

Diagnosis: ✅ healthy — disk, index, and frontmatter agree.
```

If the diagnosis is NOT healthy, it prints the rule that matched + the
suggested next step (a specific command to run or a setting to flip).

### Step 3: Offer follow-ups

After the trace, if relevant, propose ONE next step:
- Mismatch → propose `/vault-weaver-health-check` for vault-wide picture
- Many inbound wikilinks AND user rejected the concept → propose
  `/vault-wikilink-toolkit strip-slugs --slugs-file <one-entry>`
- Stale summary (summaryUpdatedAt older than recent activity) → propose
  triggering a re-synthesis via the in-plugin command

---

## Safety invariants

- **Read-only.** Never write anywhere, including not to the activity log
  itself (don't add "/trace-ran" markers).
- **Don't dump full file bodies.** Report body length, not body content.
- **Don't dump every wikilink occurrence.** Cap at 20 — the user can
  re-run with `--all` if they need more.
- **Don't propose mutations as "do you want me to fix this?"** —
  surface the EXISTING command (in-plugin or other-skill) and let the
  user invoke it. This skill is a debugger, not a fixer.

---

## Self-evolution

Propose adjustments when:

- A diagnosis rule misfires (false positive: report says "broken" but
  state is fine) → propose tightening the rule.
- A common state the user has to interpret manually keeps recurring
  → propose adding a named diagnosis rule for it.
- The user always wants to see N more inbound wikilinks than the default
  → propose changing the default cap.
- A new lifecycle phase / new frontmatter key gets added to the plugin
  → propose adding it to the report sections.

On approval: edit SKILL.md / trace_concept.py AND append to
[EVOLUTION.md](EVOLUTION.md).

## Composes with

- `/vault-weaver-health-check` — produces the full-vault picture; this
  skill is the drill-down for a single offender.
- `/vault-wikilink-toolkit` — the cleanup tool for inbound-wikilinks
  this skill surfaces.
- `/obsidian-plugin-deploy` — after deploying a fix, re-run this trace
  to confirm the specific concept is now healthy.
