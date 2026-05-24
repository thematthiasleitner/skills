#!/bin/bash
# ADVANCE deploy: commit → push → server-pull dance with askpass for the
# passphrase-protected SSH keys.
#
# Reads passphrase from stdin (line 1). Never writes it to a file other than
# transient askpass shell scripts that are shredded immediately after use.
#
# Usage:
#   echo "$PASS" | bash ~/.claude/skills/advance-deploy/_deploy.sh
#
# Or for testing without the actual SSH dance:
#   echo "$PASS" | bash _deploy.sh --check    # just verifies keys load
#
# Embedded in /advance-deploy skill.

set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/matthias/Library/CloudStorage/OneDrive-UniversitédeGenève/RA HORIZON/email_draft_automation}"
SERVER="${SERVER:-leitneruser@10.40.41.88}"
SERVER_REPO_DIR="${SERVER_REPO_DIR:-~/email_draft_automation}"
LOCAL_GITLAB_KEY="${LOCAL_GITLAB_KEY:-$HOME/.ssh/gitlab_unige}"
LOCAL_SSH_KEY="${LOCAL_SSH_KEY:-$HOME/.ssh/ssh-key}"

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then
    CHECK_ONLY=true
fi

# Read passphrase from stdin (single line, no echo)
read -r PASS

if [[ -z "$PASS" ]]; then
    echo "ERROR: no passphrase received on stdin" >&2
    exit 2
fi

# Local askpass: write transient shell script that echoes the passphrase.
ASKPASS_LOCAL=$(mktemp -t advance_askpass_local.XXXXXX.sh)
trap 'rm -f "$ASKPASS_LOCAL"' EXIT
printf '#!/bin/sh\necho "%s"\n' "$PASS" > "$ASKPASS_LOCAL"
chmod 700 "$ASKPASS_LOCAL"

# Load both keys into the local ssh-agent (ssh-add prompts via SSH_ASKPASS)
DISPLAY=:0 SSH_ASKPASS="$ASKPASS_LOCAL" SSH_ASKPASS_REQUIRE=force \
    ssh-add "$LOCAL_GITLAB_KEY" "$LOCAL_SSH_KEY" 2>&1 | tail -3

if $CHECK_ONLY; then
    echo "[check-only] keys loaded successfully; exiting before push"
    exit 0
fi

# Local push
cd "$REPO_DIR"

# Refuse to push if HEAD is behind origin/main
git fetch origin main --quiet
LOCAL_AHEAD=$(git rev-list --count origin/main..HEAD)
LOCAL_BEHIND=$(git rev-list --count HEAD..origin/main)
if [[ "$LOCAL_BEHIND" -gt 0 ]]; then
    echo "ERROR: local HEAD is BEHIND origin/main by $LOCAL_BEHIND commits. Pull/rebase first." >&2
    exit 3
fi
if [[ "$LOCAL_AHEAD" -eq 0 ]]; then
    echo "[skip] local already at origin/main; nothing to push" >&2
    # Continue to server pull anyway (server might still be behind)
fi

if [[ "$LOCAL_AHEAD" -gt 0 ]]; then
    echo "=== push: $LOCAL_AHEAD commit(s) ahead of origin/main ==="
    git log origin/main..HEAD --oneline
    echo
    git push origin main 2>&1 | tail -5
fi

# Server pull: SSH to leitneruser@... then run a NESTED askpass dance for the
# server-side gitlab_unige key. The local key was already added to the agent
# above, but agent-forwarding doesn't reach the server's git operation (the
# server uses its own ~/.ssh/gitlab_unige).
echo
echo "=== server pull ==="
SSH_INNER='
    printf "#!/bin/sh\necho %s\n" "$PASS_RECEIVED" > /tmp/askpass_srv.sh
    chmod 700 /tmp/askpass_srv.sh
    DISPLAY=:0 SSH_ASKPASS=/tmp/askpass_srv.sh SSH_ASKPASS_REQUIRE=force \
        ssh-agent bash -c "ssh-add ~/.ssh/gitlab_unige && cd ~/email_draft_automation && git pull origin main"
    EXIT=$?
    shred -u /tmp/askpass_srv.sh 2>/dev/null || rm -f /tmp/askpass_srv.sh
    exit $EXIT
'
ssh "$SERVER" "PASS_RECEIVED='$PASS' bash -c '$SSH_INNER'" 2>&1 | tail -10

echo
echo "[done] deploy complete. Run /advance-server-cycle-trigger to force a fresh cycle, or wait up to 15 min for the next auto-cycle."
