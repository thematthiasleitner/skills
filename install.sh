#!/usr/bin/env bash
# Bootstrap Claude Code skills from thematthiasleitner/skills
set -e

SKILLS_DIR="$HOME/.claude/skills"
REPO="https://github.com/thematthiasleitner/skills.git"

if [ -d "$SKILLS_DIR/.git" ]; then
  echo "Updating existing skills repo..."
  git -C "$SKILLS_DIR" pull --ff-only
else
  if [ -d "$SKILLS_DIR" ] && [ "$(ls -A "$SKILLS_DIR")" ]; then
    echo "ERROR: $SKILLS_DIR exists and is not empty. Move or delete it first."
    exit 1
  fi
  echo "Cloning skills into $SKILLS_DIR..."
  git clone "$REPO" "$SKILLS_DIR"
fi

echo "Done. $(ls "$SKILLS_DIR" | grep -v '^\.' | wc -l | tr -d ' ') skills available."
