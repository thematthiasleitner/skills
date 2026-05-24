#!/usr/bin/env bash
# Load an SSH key into ssh-agent using a passphrase passed via env var.
# Usage: GIT_PUSH_PASSPHRASE="..." _load_key.sh <key-path>
#
# Uses SSH_ASKPASS so ssh-add never tries to read from the terminal.
# The passphrase is never written to disk — it lives only in the env var
# and the temporary askpass script (which is deleted immediately after use).

set -euo pipefail

KEY_PATH="${1:?Usage: $0 <key-path>}"
PASSPHRASE="${GIT_PUSH_PASSPHRASE:?GIT_PUSH_PASSPHRASE env var required}"

# Write a minimal askpass helper to a private temp file
ASKPASS=$(mktemp)
chmod 700 "$ASKPASS"
printf '#!/bin/sh\nprintf "%%s" "%s"\n' "$PASSPHRASE" > "$ASKPASS"

# Load the key
SSH_ASKPASS="$ASKPASS" SSH_ASKPASS_REQUIRE=force ssh-add "$KEY_PATH" 2>&1
STATUS=$?

# Always clean up — passphrase must not linger on disk
rm -f "$ASKPASS"

exit $STATUS
