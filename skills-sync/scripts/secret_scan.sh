#!/usr/bin/env bash
# Scan files that `git add -A` would publish for obvious secrets.
# Repo is PUBLIC: a hit here would leak. Exit 2 on any hit. bash 3.2 compatible (macOS).
set -euo pipefail
DIR="${1:-$HOME/.claude/skills}"
cd "$DIR"

# To-be-published set: modified + untracked, honoring .gitignore.
# High-signal token shapes, plus a generic keyword rule that fires ONLY on a quoted
# literal value (so `api_key = os.environ.get(...)` / `cred.api_key` don't false-positive).
PATTERNS='AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|\bsk-[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|(password|passwd|passphrase|secret|api[_-]?key|access[_-]?token|client[_-]?secret|bearer)["'"'"' ]*[:=][ ]*["'"'"'][A-Za-z0-9/+_.-]{16,}["'"'"']'
# Lines that look like a hit but are env lookups / placeholders / examples — drop them.
EXCLUDE='os\.environ|process\.env|getenv|import\.meta|your[_-]?(api|secret|token|key)|example\.com|changeme|placeholder|redacted|<[a-z0-9_-]+>|xxxx+|\$\{?[A-Z_]+\}?'

HITS=0
COUNT=0
while IFS= read -r -d '' f; do
  COUNT=$((COUNT+1))
  # -I skips binary files
  m="$(grep -InEi "$PATTERNS" "$f" 2>/dev/null | grep -viE "$EXCLUDE" || true)"
  if [ -n "$m" ]; then
    echo "$m"
    echo "  ^ in $f"
    HITS=1
  fi
done < <(git ls-files -mo --exclude-standard -z)

echo
if [ "$COUNT" -eq 0 ]; then
  echo "Nothing to scan (no changes)."
  exit 0
fi
if [ "$HITS" -ne 0 ]; then
  echo "POTENTIAL SECRETS found above across $COUNT staged file(s). Repo is PUBLIC."
  echo "Review each hit. Do NOT publish until resolved (move secret out, or .gitignore the file)."
  exit 2
fi
echo "Secret scan clean ($COUNT file(s) checked)."
