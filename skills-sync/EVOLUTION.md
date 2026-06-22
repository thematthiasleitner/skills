# skills-sync — evolution log

- **2026-06-22** — Created. `~/.claude/skills` is the canonical public repo
  (`thematthiasleitner/skills`, branch `main`). Three sync directions: `publish` (local → GitHub,
  secret-scan-gated because the repo is public), `update` (GitHub → this machine), `install`
  (bootstrap a new account/machine via `install.sh`, or an org/project repo via
  `npx skills add --project --copy`). Composes `git-push` for the SSH push. Scripts: `status.sh`,
  `secret_scan.sh` (bash 3.2-safe), `gen_readme.py` (regenerates the README skills table).
- **2026-06-22** — First publish (commit `ce2b840`: skills-sync + 25 untracked skills + README). SSH
  push failed — neither `~/.ssh/ssh-key` (the git-push key-map default; wrong identity) nor
  `~/.ssh/github_thematthiasleitner` authenticate to this repo (`Permission denied (publickey)`).
  Pushed via the `gh` HTTPS credential helper instead, then repointed `origin` to HTTPS and set
  `credential.helper='!gh auth git-credential'` so `git push`/`pull`/`fetch` (and `status.sh`) work
  passphrase-free. Made gh HTTPS the primary push path in SKILL.md; dropped the `git-push` dependency.
  If SSH is wanted later, register a working key on the `thematthiasleitner` GitHub account first.
