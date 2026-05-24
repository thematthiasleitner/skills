# Evolution log — git-push

## 2026-05-24 — Skill created

Built because SSH passphrase auth blocked every `git push` attempt
from within Claude Code (no interactive terminal for ssh-add).

Key design decisions:
- `SSH_ASKPASS` + temp script pattern — avoids `expect`, works on macOS
  without any extra deps; temp file is deleted immediately after ssh-add
- Passphrase passed via `GIT_PUSH_PASSPHRASE` env var (not CLI arg)
  so it never appears in `ps` output
- Key map baked into SKILL.md: `github.com → ssh-key`,
  `gitlab/unige → gitlab_unige`
- Force-push hard-blocked — requires explicit user instruction
- Main/master branch push requires confirmation
