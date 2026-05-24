#!/bin/bash
# Trigger one-shot manual export cycle on ADVANCE production server.
# Designed to be piped over SSH:
#
#   ssh leitneruser@10.40.41.88 'bash -s' < _trigger.sh
#
# Embedded in /advance-server-cycle-trigger skill.

set -uo pipefail   # NOT -e: we want the trap to capture exit code on failure too

cd ~/email_draft_automation

# Source qualtrics env vars (token + datacenter)
set -a
source qualtrics/qualtrics_env.sh
set +a

# Force live workbook + server runtime status
unset QUALTRICS_WORKBOOK_PATH
export QUALTRICS_WORKBOOK_MODE=live
export QUALTRICS_RUNTIME_STATUS=server

echo "=== one-shot export ==="
echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# Unbuffered (-u) is MANDATORY — without it, stdout stays buffered until
# process exit, so a hang or OOM looks identical to "still running"
# (the 2026-05-13 OOM was invisible for 21 hours because of buffering).
timeout 180 .venv/bin/python3 -u qualtrics/export_responses_to_contacts.py 2>&1 | tail -25
EXIT=${PIPESTATUS[0]}

echo
echo "finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "EXIT=$EXIT"
exit $EXIT
