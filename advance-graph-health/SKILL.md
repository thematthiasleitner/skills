---
name: advance-graph-health
description: Read-only health verdict for the ADVANCE Microsoft Graph mail auth — is the token alive, since when is it dead, which cycle jobs are failing on it, and which re-auth path applies (mode-aware, delegated vs MS_AUTH_MODE=app). Use when cycle jobs fail with MissingGraphToken, reply/categorize/sent_log go red, a Graph script can't acquire a token, or before/after any re-auth to verify recovery. Composes with advance-cycle-status (general cycle health) and request-ssh-access (server reachability).
---

# advance-graph-health

Answers three questions, read-only: **is the Graph token alive? since when
not? what's the correct re-auth path right now?**

## Quick start (all on the server — local token copies are usually stale)

**1. Token probe** (mode-aware):

```bash
ssh leitneruser@10.40.41.88 'cd ~/email_draft_automation && set -a && source .env && set +a && .venv/bin/python3 - <<EOF
import sys, os
sys.path.insert(0, os.path.expanduser("~"))
from email_draft_automation.src import graph_mail as gm
mode = os.environ.get("MS_AUTH_MODE", "delegated")
print("auth mode:", mode)
tm = gm.GraphTokenManager(os.environ["MS_TENANT_ID"], os.environ["MS_CLIENT_ID"])
try:
    tm.acquire_token(); print("token: ALIVE")
except Exception as e:
    print("token: DEAD —", e)
    if mode == "delegated":
        a = tm.app.get_accounts()
        print("cached accounts:", [x.get("username") for x in a],
              "| silent:", tm.app.acquire_token_silent(gm.SCOPES, account=a[0]) if a else None)
EOF'
```

**2. Blast radius + time of death** (journal):

```bash
ssh leitneruser@10.40.41.88 'journalctl -u email-draft-automation-cycle.service --since "-48h" --no-pager \
  | grep -E "MissingGraphToken|Cycle completed" | grep -B1 "failure" | head; \
  journalctl -u email-draft-automation-cycle.service --since "-48h" --no-pager \
  | grep "Cycle completed successfully" | tail -1'
```

Last `successfully` line vs first `MissingGraphToken` = the outage window.
Graph-dependent jobs: `categorize_emails`, `reply_drafts`, `sent_log` scan,
bounce scan, draft creation. Non-mail jobs (export, survey publish, rclone)
keep running — a red mail job with a green export is the token signature.

**3. Verdict + the correct re-auth path:**

- `MS_AUTH_MODE=app` (client-credentials, ADR 0006): no refresh token exists;
  failure means credential expired/revoked or Application Access Policy
  changed → IT, not re-auth.
- delegated (default): **device-code flow is PERMANENTLY CA-blocked
  (AADSTS53003, Kali365 mitigation) — never re-run `scripts/authorize_graph.py`.**
  Path = interactive auth-code sign-in on the Mac → scp the produced
  `ms_token.json` to server `~/email_draft_automation/` → next 15-min cycle
  auto-recovers, no deploy.
- After re-auth: re-run probe 1, then wait one cycle tick and confirm
  `Cycle completed successfully` with zero `MissingGraphToken`.

## Preconditions

- SSH to the server loaded (else run `/request-ssh-access` first).
- Read-only — no agent-lock needed.

## Composes with

- **advance-cycle-status** — general deploy/cycle health; this skill is the
  Graph-auth-specific deep dive when that shows mail-job failures.
- **request-ssh-access** — satisfy SSH precondition.
- **graph-drafts-tree** — once the token is alive, verify mailbox state.

## Test

None — verdict depends on live server, journal, and tenant CA state; a
mocked runner would assert nothing real. (Recorded per session-harvest
Phase 3 skip rule.)

## History

Built from the 2026-06-10/11 outage (memory:
`project-graph-token-ca-incident`): token died at 08:31 via a tenant CA
rollout, diagnosis cost hours because silent-refresh death, journal blast
radius, and "which re-auth flow is even allowed" were rediscovered ad hoc.
