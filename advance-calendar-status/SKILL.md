---
name: advance-calendar-status
description: Read-only staleness verdict for the ADVANCE advance-project@unige.ch Outlook calendar — runs sync_calendar --dry-run on the server and reports the desired-vs-live diff (created/updated/deleted/skipped, broken down by canton), the last-good-sync time, and the next nightly fire, so you can tell whether the calendar is current. Calendar sync is NIGHTLY-ONLY (not the 15-min cycle), so a failed or skipped nightly leaves Outlook stale until the next night. Use when asked "is the calendar up to date / current", after a Graph-token outage or any failed nightly, or before relying on calendar event times. Optional guarded apply (a real sync) only on explicit consent. Composes with advance-graph-health, advance-lock, request-ssh-access, advance-cycle-status.
---

# advance-calendar-status

The Outlook calendar for `advance-project@unige.ch` is a **derived view** of the workbook, rebuilt by `sync_calendar`. That sync runs **nightly only** — `email-draft-automation-email-drafts.timer` at **00:00** (NOT the 15-min export cycle). So if a nightly fails (e.g. inside a Graph-token outage) or the workbook changes during the day, the calendar is **stale until the next 00:00**. This skill tells you whether it's current, and optionally closes the gap.

## Preconditions (satisfy before the server op)

1. **Graph token alive** — the dry-run hits Graph. If you suspect a token outage, run `advance-graph-health` first; a dead token makes this fail with `MissingGraphToken`, which is a token problem, not a calendar problem.
2. **SSH key loaded** — `request-ssh-access` for `~/.ssh/ssh-key` if `ssh-add -l` doesn't show it.
3. **Agent-lock held** — the lock guard fail-closed-blocks *all* server SSH, even a read-only dry-run. Claim it under the **default identity** (`user@host`, not `ADVANCE_AGENT_ID`): `python3 tools/agent_lock.py claim "<task>"` from any current clone. Release when done.

## Phase 1 — Verdict (read-only, default)

```bash
ssh -o IdentitiesOnly=yes -i ~/.ssh/ssh-key leitneruser@10.40.41.88 \
  'cd ~/email_draft_automation && QUALTRICS_WORKBOOK_MODE=live \
   .venv/bin/python3 -m qualtrics.sync_calendar --dry-run 2>&1 \
   | grep -iE "desired events|done:"'
```

Interpret the `done: created=C updated=U deleted=D skipped=S` line — it's the diff between the workbook (desired) and the live calendar:

- **all zero** → calendar is current. Done.
- **created>0** → events the calendar is missing (new course sessions not yet pushed).
- **updated>0** → events present but with stale fields (time/location/title changed in the workbook).
- **deleted>0** → events on the calendar the workbook no longer wants.

To see *which* events (e.g. confirm a jump in `desired events` is legit), break the dry-run's per-event lines down by canton:
```bash
… --dry-run 2>&1 | grep -iE "course:" | sed -E "s/.*course:([A-Z]+)_.*/\1/" | sort | uniq -c
```

Cross-check timing: the last successful sync and the next nightly —
```bash
ssh … 'systemctl list-timers --all | grep email-drafts; \
        journalctl -u email-draft-automation-email-drafts.service --since "-2 days" \
        | grep -iE "sync_calendar.*(done:|FAIL)"'
```

Report: current vs stale, the diff counts (and canton breakdown if non-trivial), last-good-sync, next nightly. **If stale, this is a finding — let the user decide whether to apply now or wait for the nightly self-heal.**

## Phase 2 — Apply (guarded; explicit consent only)

A real sync writes to the **live shared calendar**. Outward-facing mutation → propose via `AskUserQuestion`, never silently. Only touches our GUID-tagged events; the dry-run already proved the diff is clean.

```bash
ssh … 'cd ~/email_draft_automation && QUALTRICS_WORKBOOK_MODE=live \
   .venv/bin/python3 -m qualtrics.sync_calendar 2>&1 | grep -iE "desired events|done:"'
```

**Then re-run Phase 1** and confirm `created=0 updated=0 deleted=0` before reporting done. Release the agent-lock.

**Rollback** (only deletes events carrying our GUID; manual entries untouched):
```bash
QUALTRICS_WORKBOOK_MODE=live .venv/bin/python3 -m qualtrics.sync_calendar --delete-all-tagged
```

## Sticky facts

- Extended-property GUID `6b3d1f5a-c8e2-4b7a-9c4f-5d3e1a2b6c8f` is **frozen** — changing it orphans every tagged event.
- Workbook is source of truth; the calendar is never written back to the workbook.
- A big jump in `desired events` (e.g. 105→205) is usually legit new sessions, but if the dry-run shows many `created` at once, eyeball the canton breakdown before applying.

## Composes with

- **`advance-graph-health`** — run first if a token outage is plausible (this skill needs a live Graph token).
- **`advance-lock`** — claim before any server op here; the guard blocks otherwise.
- **`request-ssh-access`** — load `~/.ssh/ssh-key` first.
- **`advance-cycle-status`** — sibling: that one is the 15-min export cycle, this one is the nightly calendar sync.

## Regression guard (no bundled test by design)

Calendar-sync correctness is already guarded nightly by the repo's Layer C `calendar-dry-run` check (`tools/layer_c_smoke.py`) — it asserts the dry-run diff is clean. This skill's behaviour is live-server + Graph dependent with no hermetic surface, so it ships **no parallel test**; the Layer C check is the harness.
