---
name: session-harvest
description: Turn a finished work session into durable assets — extract the lessons, mint small composable skills for the recurring procedures, and add a runner test to each new skill when (and only when) one would earn its keep. Use at the end of a session, after a hard-won fix, or when the user says "harvest this", "extract the lessons", "make a skill from what we just did", or "housekeeping". Propose-first: it writes nothing until you approve the harvest report. Composes existing skills (remember / revise-claude-md, write-a-skill, tdd) rather than reimplementing them, and is itself decomposed into three independently-invokable phases.
---

# session-harvest

A **thin orchestrator**. It does not reimplement lesson-capture, skill-authoring, or test-writing — it sequences the skills that already do those, and adds the connective judgment: *what is worth keeping, what is worth a skill, and what is worth a test.*

## Composability contract

The skill is built to be taken apart. Three phases, each a standalone entrypoint with a single responsibility, each callable on its own or by another skill:

| Invocation | Runs | Use alone when |
|---|---|---|
| `/session-harvest` | all three phases, in order | wrapping up a session |
| `/session-harvest harvest` | Phase 1 only → report | you just want the lessons surfaced/routed |
| `/session-harvest mint <pattern>` | Phase 2 on one named pattern | you already know the skill you want |
| `/session-harvest test <skill-path>` | Phase 3 on one existing skill | retrofitting a runner test |

Each phase reads a plain-text artifact and writes a plain-text artifact, so phases compose in any order and other skills can call a single phase. Nothing here is load-bearing on the others having run.

## Phase 0 — Inventory first (gates every proposal)

**No proposal is made before surveying what already exists.** Run this once at the start of any invocation; every later phase reads its result, so the report never proposes something that duplicates an installed asset.

1. **Existing skills** — `ls ~/.claude/skills/` and grep their `SKILL.md` descriptions (plus plugin skills surfaced in the session list). For each candidate, the verdict is one of: **new** (nothing close), **extend `<skill>`** (a skill covers the same domain — add to it, don't fork), or **already-covered** (reject; name the skill).
2. **Existing memories — grep BODIES, not just the index.** `rg -i '<term>' <memory-dir>` across the whole memory directory, NOT only `MEMORY.md`. A lesson already sitting in a memory file's **body** is already-covered even when its filename/description don't mention it (the 2026-06-18 miss: a slack-lists gotcha was re-proposed although it was already at `reference_task_dashboard_slack` line 41). Verdict per memory candidate: **new file** / **append to `<file>`** / **already-covered: `<file>`**.
3. **Existing tests / harnesses** — before any Phase-3 test, look for one to extend: repo `tests/test_*.py`, the Layer C smoke checks (`tools/layer_c_smoke.py`), `make` test targets, and any `runner.sh` already inside the target skill. A new standalone test is the last resort, not the default.

Every line in the harvest report carries its Phase-0 verdict (`new` / `extends X` / `reuses harness Y` / `already-covered: Z`). If you can't cheaply tell whether something exists, say so rather than assume it's new.

## The pipeline

### Phase 1 — Harvest lessons

Scan the session for **durable, reusable signal** and route each item. Sources, in priority order:

1. The current conversation (errors hit + how they were fixed, gotchas, decisions, repeated multi-step procedures).
2. `MEMORY.md` + recent memory files — what was *just* learned that isn't captured yet.
3. Recent diffs / commits / deploys this session, if any.

For each candidate, classify the **route**:

- **memory-only** — a durable fact or gotcha that passes the reuse test below (NOT a one-off). → hand to `remember` (or `claude-md-management:revise-claude-md` if it belongs in CLAUDE.md). Not every lesson deserves a skill. **Default to appending to an existing memory file** (the one the Phase-0 body grep surfaced); mint a NEW file only when no existing file is a reasonable home AND a distinct future task would recall it. A new file ⇒ a new `MEMORY.md` index line ⇒ treat as costly (the index has a size budget — keep it lean).
- **skill-worthy** — a procedure that was *non-obvious*, *multi-step*, and *will recur*. → Phase 2.
- **both** — recurring procedure whose rationale also belongs in memory.

**The reuse test — apply to EVERY candidate before keeping it:** *would an agent on a **different** future task act differently because this was written down?* If no → reject. This kills fix-narratives ("what we did this session"), the verified-outcome victory lap, and anything already recorded in git / config / CLAUDE.md. Also reject: trivial, already covered by an existing skill (grep `~/.claude/skills/*/SKILL.md`) or by a memory **body** (the Phase-0 grep), or single-task with no reuse. Keep the *smallest durable nugget* — the non-obvious rule a future agent would trip on, not the play-by-play. Surface what you rejected and why — silent dropping reads as "covered everything."

**Output:** the *harvest report* (see Propose-first). Writes nothing yet.

### Phase 2 — Mint composable skills

For each skill-worthy pattern, honor its Phase-0 verdict first: if it's **extend `<skill>`**, edit that skill instead of creating a near-duplicate; only **new** patterns get a fresh skill. Then invoke **`write-a-skill`** to scaffold (or extend). Enforce composability on every skill minted — this is the whole point:

- **Single responsibility.** One verb. If it needs "and", split it.
- **Standalone-invocable**, and **callable as a step** by other skills. State both in the description.
- A **`## Composes with`** section naming the skills it chains to/from.
- An **access/precondition** contract if it needs one (lock, ssh key, dry-run gate), so callers know what to satisfy first.
- Prefer **propose-first / dry-run default** for anything that mutates state, matching workspace norms.

### Phase 3 — Add a runner test, *when reasonable*

For each minted skill, first decide **whether a test earns its keep**. Add one only when the skill has deterministic, scriptable behavior; skip otherwise and record the skip reason. Before writing anything, check the Phase-0 test inventory: if a harness already covers the behavior (a Layer C check, a `make` target, an existing `tests/test_*.py`), **extend it** rather than minting a parallel test.

**Add a runner test when** the skill: parses/transforms data, does file ops, hits an API with a checkable round-trip, or asserts an invariant. **Skip when** the skill is pure instruction or judgment (communication style, "zoom out", interview/grilling, planning prose) — a test there is theater.

Pick the form to fit the skill:

- **`runner.sh` smoke** — shell script exercising the deterministic path, exit non-zero on failure. Default for ops/CLI/file skills; language-agnostic; wires into Layer-C-style CI.
- **Hermetic `pytest`** — red→green test file. Use for Python-logic skills where assertions matter.

Bundle the test inside the skill's own directory (`runner.sh` or `test_<skill>.py`) so the skill stays self-verifying and portable.

## Propose-first protocol (runtime default)

A full run is **dry-run until approved.** Produce one *harvest report* and stop:

```
HARVEST REPORT
── Lessons (routed) ───────────────────────────────
  [memory]  <one-liner>            → remember / revise-claude-md
  [skill ]  <pattern>              → mint  <proposed-skill-name>   (new)
  [both  ]  <pattern>              → extend <existing-skill> + memory
  [reject]  <candidate>            → already-covered: <skill> / trivial / one-off
── Skills (Phase-0 verdict) ──────────────────────
  <name>  — <one-line desc>  | new | extends <skill>  | composes with: <…>
           | test: extends <harness> | runner.sh | pytest | none (<reason>)
── Nothing is written until you approve. Reply to approve all, or prune. ──
```

Each row shows its Phase-0 verdict so you can see, before approving, that every proposal already accounts for what exists.

Only after approval: run Phase 2 + 3 and the memory hand-offs. Honor any pruning. Never write a skill or test the user struck from the report.

## Composes with

- **`remember` / `claude-md-management:revise-claude-md`** — Phase 1 hand-off for memory-route lessons.
- **`write-a-skill`** — Phase 2 scaffolding engine.
- **`tdd`** — Phase 3 test authoring for the pytest form.
- **`handoff`** — run before this to checkpoint, or after to record what was harvested.
- **`archive-stale`** — the file-tidying counterpart; this is the *knowledge*-tidying counterpart.

## Self-evolution

When a session keeps producing the same *kind* of skill, add a short recipe for it here. If a routing call was wrong (minted a skill that should've been memory, or vice-versa), tighten the Phase 1 criteria above so the next harvest is sharper.

### Recipe: surface a MEMORY.md trim when the index is over budget

A harvest *adds* to memory, so it's the natural moment to also notice the index has outgrown its budget and offer a trim. Treat this as a **housekeeping line in the harvest report** (not a lesson route), propose-first like everything else.

- **Trigger.** The session shows a `MEMORY.md is NN KB (limit: MM KB)` warning, or `wc -c MEMORY.md` exceeds the limit, or you just appended an entry. Measure before proposing: `wc -c MEMORY.md`; longest lines via a tiny `python3` length sort (plain `sort` chokes on non-ASCII paths/emoji — use Python).
- **Root cause is almost always the same.** Index lines grew from one-line hooks into mini-paragraphs that duplicate detail already in the topic files (embedded MR numbers, deploy tags, multi-clause status histories).
- **The fix = compress, don't delete.** Rewrite each over-long entry to a terse recall hook (`slug — what it is + current status`); the full detail stays in the topic `.md` (linked), so **no information is lost** and recall still works. Default to shortening; only *drop* an index line (topic file stays on disk, still recallable) for a few fully-closed one-off incidents, and only if the user opts in.
- **Offer tiers by scope** (compress >400ch / >300ch / all >200ch), each with an estimated post-trim file size, and recommend the one that lands under budget with growth headroom (the index grows ~1 entry/session).
- **The real gate is file size, not line length.** `[name.md](name.md)` duplicates the filename, so a long slug costs ~90–110 chars of unavoidable link overhead before any hook — lines for long slugs will still measure >200 chars even with a tight hook. Verify success by `wc -c` under the limit, not by a per-line char cap. If the user wants strictly short *lines*, the lever is shortening the **display title** (`[short title](real_filename.md)`), which trades slug glanceability.
- **Composes with** `remember` (the per-file writer) — this recipe tidies the *index* that `remember` appends to.
