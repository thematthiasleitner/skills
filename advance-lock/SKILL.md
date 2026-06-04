---
name: advance-lock
description: Claim / renew / release / check the ADVANCE multi-agent mutex before LIVE or server operations. The lock is a server-side atomic directory (~/email_draft_automation/.agent_lock.d/) managed by tools/agent_lock.py; the PreToolUse hook .claude/hooks/agent_lock_guard.sh fail-closed-blocks deploy / cycle-trigger / Qualtrics --apply / e2e / live-export / server-SSH-mutation unless the calling agent holds it. Invoke when about to do live/server work (so the guard lets you through), when blocked by the agent-lock guard, or to see who currently holds the lock. Phase 2 of docs/multi_agent_workflow.md.
---

# advance-lock — multi-agent mutex for ADVANCE live/server ops

The enforcement (the PreToolUse hook) does the blocking automatically. This skill
is the ergonomic wrapper around `tools/agent_lock.py` for the human-driven
claim/release lifecycle. Run from an `email_draft_automation` checkout with the
SSH key loaded (the lock lives on the production server, reached over SSH).

## Identity
You are `$ADVANCE_AGENT_ID`, else `<user>@<short-host>`. Set `ADVANCE_AGENT_ID`
to distinguish two agents on the same machine/user.

## Commands

```bash
# Before any live/server op (deploy, cycle-trigger, Qualtrics --apply, e2e):
python3 tools/agent_lock.py claim "zoom 6A live apply"   # acquire (steals if expired)
python3 tools/agent_lock.py status                        # who holds it / am I valid?
python3 tools/agent_lock.py renew                         # during long work (TTL default 1h)
python3 tools/agent_lock.py release                       # ALWAYS release when done
```

## Workflow
1. **Claim** before live work. If it prints `HELD_BY:<other>` → another agent is
   mid-operation; wait or coordinate. Do NOT force.
2. Do the live op (deploy / `--apply` / e2e). The guard hook verifies you hold the
   lock and lets it through; if you forgot to claim it BLOCKS you (fail-closed).
3. **Renew** if the work runs past the TTL (default 3600s).
4. **Release** as soon as you're done so the other agent isn't blocked. A crashed
   agent's lock auto-expires after its TTL (stealable), so the project never wedges.

## When blocked by the guard
The block message tells you why: held by another agent (wait), free but unclaimed
(claim it), or unverifiable (load `~/.ssh/ssh-key` into ssh-agent / check UNIGE VPN
— the guard is fail-closed by design).

## Notes
- Gated commands (what the guard intercepts) are defined in `GATED_PATTERNS` in
  `tools/agent_lock.py` and mirrored in `.claude/hooks/agent_lock_guard.sh`. Keep
  them in sync if you add a new live-op entry point.
- Read-only work, dry-runs, `make test-*`, and feature-branch git are NOT gated —
  no lock needed.
- Full design + rationale: `docs/multi_agent_workflow.md` (Phase 2).
