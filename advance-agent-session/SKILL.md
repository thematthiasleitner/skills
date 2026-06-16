---
name: advance-agent-session
description: Preflight to run ONCE at the start of any ADVANCE server/live session, before advance-lock / advance-deploy / live-workbook work. Detects the failure modes that wreck throughput — working in the OneDrive tree or a shared clone instead of an isolated per-agent clone off origin/main (use scripts/new-agent.sh; ADR 0004), a stale base, the SAME default agent-lock id (user@host) so the mutex can't serialize concurrent sessions, another agent already holding the lock, a dirty/foreign-branch working tree, and the agent-lock guard's cold-handshake SSH checks fail-closed-timing-out under cycle load. Sets a distinct ADVANCE_AGENT_ID, warms an SSH ControlMaster for the server, and prints a clear "safe to do live work?" verdict. **Read-only diagnostics + local config only — low risk. Invoke at session start, or whenever lock contention / guard SSH-timeout blocks / shared-tree surprises appear.**
tools: Bash, Read, Edit
---

# ADVANCE Agent Session Preflight

Run this **before** the first live/server op of a session. It surfaces — up front,
in seconds — the environment hazards that otherwise show up as mid-deploy surprises:
repeated lock contention, guard fail-closed SSH timeouts, and shared-working-tree
clobbering.

## What it checks (all read-only) + fixes (local only)

### 1. Working tree — are you in an isolated clone off origin/main?
```bash
pwd; git rev-parse --show-toplevel 2>/dev/null
git branch --show-current; git status -sb | head -3      # behind N? dirty?
git log -1 --format='%h %cr' origin/main 2>/dev/null      # how current is your base?
```
- ✅ **Good:** an isolated clone at `~/dev/<task-id>/email_draft_automation`, on a
  `task/<id>` branch, current with `origin/main` — what `scripts/new-agent.sh
  <task-id>` produces. Each agent gets its OWN clone (own `.git`), so there is no
  cross-agent clobber hazard.
- ⛔ **Bad:** the **OneDrive tree** (`…/RA HORIZON/…`) or the **retired
  `advance-matthias` shared clone** — these caused the 2026-06-05 cross-agent
  commit + the 2026-06-08 stale-base near-miss. → Switch now:
  `scripts/new-agent.sh <task-id>`; already mid-work there? follow
  `docs/agent_onedrive_to_gitlab_migration.md`. (The old
  `~/dev/email_draft_automation → advance-matthias` symlink has been removed.)
- ⛔ **Stale base:** if `git status` says "behind N", rebase on `origin/main`
  before working — never deploy from a stale tree.

### 2. Agent identity — can the mutex actually serialize us?
```bash
echo "ADVANCE_AGENT_ID=${ADVANCE_AGENT_ID:-<unset -> defaults to $(whoami)@$(hostname -s)>}"
```
- The agent-lock id defaults to `user@short-host`. **Two concurrent sessions by the
  same user on the same machine collapse to the SAME id**, so the mutex can't tell
  them apart (this caused the 2026-06-04 ping-pong). It also can't be fixed
  mid-session: the guard hook reads the id from the *harness* environment, not from
  an inline `VAR=… cmd` prefix.
- **Durable fix (launch-time):** start each concurrent session with a distinct id —
  `ADVANCE_AGENT_ID=<session-tag> claude …`. Then `tools/agent_lock.py status` shows
  the other session as "held by OTHER" (accurate) and the guard protects both ways.
- If you're already mid-session with the default id AND another agent may be
  active, **treat the mutex as advisory**: before each live step re-read the lock
  meta and abort if the `task=` label isn't yours (the lock-task guard pattern).

### 3. Lock state — is someone live right now?
```bash
ssh leitneruser@10.40.41.88 'cat ~/email_draft_automation/.agent_lock.d/meta 2>/dev/null || echo FREE'
```
Report holder / task / heartbeat-age. If held by another task (and not stale per
ttl), **do not steal** — wait or coordinate.

### 4. Warm the SSH ControlMaster (stops guard fail-closed timeouts)
The agent-lock guard SSHes to the server on *every* gated command; cold handshakes
intermittently exceed its timeout and fail-closed-BLOCK you under cycle load. Warm
a shared connection so those checks reuse it:
```bash
grep -q '^Host 10.40.41.88' ~/.ssh/config || cat >> ~/.ssh/config <<'CFG'
Host 10.40.41.88
  User leitneruser
  IdentityFile ~/.ssh/ssh-key
  IdentitiesOnly yes
  ControlMaster auto
  ControlPath ~/.ssh/cm-%r@%h:%p
  ControlPersist 10m
  ConnectTimeout 20
CFG
ssh -fN leitneruser@10.40.41.88 && ssh -O check leitneruser@10.40.41.88
```
⚠️ **Gotcha:** the master is opened without `-A`, so a *reused* connection has no
agent forwarding. For a server `git fetch`/pull via the **forwarded** gitlab key,
bypass the master: `ssh -A -o ControlPath=none … GIT_SSH_COMMAND='ssh -o IdentitiesOnly=no -o IdentityAgent=$SSH_AUTH_SOCK' git fetch` (see `advance-deploy`).

### 5. Verdict
Print a one-screen summary: clone (shared?/branch/clean?), agent-id
(distinct?/shared-default?), lock (free/held-by-other), ControlMaster (up?), and a
**GO / COORDINATE-FIRST** recommendation for live work.

## When to invoke
- At the **start** of any session that will deploy / sweep / trigger a cycle / edit
  the live workbook / hold the agent-lock.
- Whenever you hit repeated lock contention, "server unreachable (SSH timeout)"
  guard blocks, or discover another agent active.

## Safety invariants
- Read-only except: appending the ControlMaster block to `~/.ssh/config` (idempotent,
  guarded by the `grep -q`) and, if asked, writing `ADVANCE_AGENT_ID` to settings.
- **Never steal a non-stale lock** held by another task. Never `git add .` / checkout
  over a foreign dirty tree.

## Composes with
- `/advance-lock` — claim/renew/release once preflight says GO
- `/advance-deploy`, `/advance-server-cycle-trigger`, `/advance-durable-workbook-fix`
  — all assume a clean session this skill establishes
- `docs/multi_agent_workflow.md` — the shared-clone / one-writer protocol this enforces
