#!/usr/bin/env bash
# Read-only sync status for the skills repo: ahead/behind origin, modified + untracked skills.
set -euo pipefail
DIR="${1:-$HOME/.claude/skills}"

if [ ! -d "$DIR/.git" ]; then
  echo "No git repo at $DIR — this machine isn't bootstrapped. Run install (see SKILL.md)."
  exit 1
fi
cd "$DIR"

REMOTE="$(git remote get-url origin 2>/dev/null || echo '(no origin)')"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "repo:   $DIR"
echo "remote: $REMOTE"
echo "branch: $BRANCH"
echo

# Refresh remote tracking without changing the working tree.
git fetch --quiet origin "$BRANCH" 2>/dev/null || echo "(fetch failed — offline? counts below are vs last-known origin)"

UP="origin/$BRANCH"
if git rev-parse --verify --quiet "$UP" >/dev/null; then
  AHEAD="$(git rev-list --count "$UP..HEAD" 2>/dev/null || echo '?')"
  BEHIND="$(git rev-list --count "HEAD..$UP" 2>/dev/null || echo '?')"
  echo "ahead of $UP:  $AHEAD commit(s) to publish"
  echo "behind $UP: $BEHIND commit(s) to update"
else
  echo "(no $UP tracking ref yet)"
fi
echo

MOD="$(git ls-files -m | sed 's#/.*##' | sort -u)"
UNT="$(git ls-files -o --exclude-standard | sed 's#/.*##' | sort -u)"
echo "modified skills:"
[ -n "$MOD" ] && echo "$MOD" | sed 's/^/  /' || echo "  (none)"
echo "untracked (never-published) skills:"
[ -n "$UNT" ] && echo "$UNT" | sed 's/^/  /' || echo "  (none)"
echo
if [ -n "$MOD" ] || [ -n "$UNT" ]; then
  echo "=> uncommitted local changes. Run 'publish' to push them up."
else
  echo "=> working tree clean."
fi
