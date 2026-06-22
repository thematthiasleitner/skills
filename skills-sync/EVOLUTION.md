# skills-sync — evolution log

- **2026-06-22** — Created. `~/.claude/skills` is the canonical public repo
  (`thematthiasleitner/skills`, branch `main`). Three sync directions: `publish` (local → GitHub,
  secret-scan-gated because the repo is public), `update` (GitHub → this machine), `install`
  (bootstrap a new account/machine via `install.sh`, or an org/project repo via
  `npx skills add --project --copy`). Composes `git-push` for the SSH push. Scripts: `status.sh`,
  `secret_scan.sh` (bash 3.2-safe), `gen_readme.py` (regenerates the README skills table).
