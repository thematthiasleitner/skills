---
name: skills-sync
description: Sync your personal Claude skills through the thematthiasleitner/skills GitHub repo so the same skill set is available on every Claude account/machine and can be injected into org or project ecosystems. Use when the user says "sync skills", "push/publish my skills", "save skills to GitHub", "install my skills on another machine/account", "update skills from GitHub", or "add my skills to a project/org repo".
tools: Bash, AskUserQuestion
---

# skills-sync

One GitHub repo — `thematthiasleitner/skills` — is the single source of truth for the user's
personal Claude skills. `~/.claude/skills/` on this machine **is** that repo (git remote
`git@github.com:thematthiasleitner/skills.git`, branch `main`, **public**). Every skill is a real
copied dir (not a symlink), so it commits cleanly. This skill keeps that repo and every consumer in
sync.

## Three places skills live

| Target | Path | How to get the skills there |
|---|---|---|
| **This machine, all agents** (canonical) | `~/.claude/skills/` | already the git repo — `publish` / `update` below |
| **A new account / new machine** (global) | `~/.claude/skills/` | bootstrap: `install.sh` or clone |
| **An org / project ecosystem** | `<repo>/.claude/skills/` | `npx skills add … --project --copy`, then commit into that repo |

`--copy` (not symlink) matters everywhere: copied skills are committable and survive the npx cache
being cleared.

## Always run `status` first

```bash
bash ~/.claude/skills/skills-sync/scripts/status.sh
```

Reports: ahead/behind vs `origin/main`, modified skills, untracked (never-pushed) skills. Read-only.
Use it to decide whether to `publish` or `update`.

---

## publish — local skills → GitHub (push up)

Use when the user changed/added skills locally and wants them on GitHub (→ all other accounts).

1. **Secret scan — mandatory, repo is PUBLIC.**
   ```bash
   bash ~/.claude/skills/skills-sync/scripts/secret_scan.sh
   ```
   Scans every modified + untracked file `git add -A` would publish for API keys, tokens, private
   keys, passphrases. Exit ≠ 0 → **stop**, show hits, ask the user before continuing. Never publish a
   secret to a public repo.

2. **Regenerate the README skills table** so it never goes stale:
   ```bash
   python3 ~/.claude/skills/skills-sync/scripts/gen_readme.py
   ```

3. **Stage, review, commit:**
   ```bash
   cd ~/.claude/skills
   git add -A
   git status --short        # show the user exactly what will be committed
   git commit -m "Sync skills: <one-line summary of what changed>"
   ```
   Summarise added/modified skills in the message. Don't commit if `git status` is empty.

4. **Push.** `origin` is HTTPS with the `gh` credential helper wired in, so a plain push just works —
   no passphrase:
   ```bash
   git push
   ```
   (Equivalent explicit form: `git -c credential.helper='!gh auth git-credential' push
   https://github.com/thematthiasleitner/skills.git main`.) Requires `gh auth status` logged in as
   `thematthiasleitner`. SSH is **not** wired for this repo — the keys on this machine
   (`~/.ssh/ssh-key`, `~/.ssh/github_thematthiasleitner`) don't authenticate to it; don't route
   through `/git-push` unless a working registered key is later added.

5. **Confirm:** `git log @{u}..HEAD --oneline` returns empty.

## update — GitHub → this machine (pull down)

Use on a machine that already has the repo, to pick up skills published elsewhere.

```bash
cd ~/.claude/skills && git pull --ff-only
```

If `--ff-only` fails (local commits diverge), run `status`, surface the divergence, and let the user
choose rebase vs merge. Never auto-force.

## install — bootstrap a new account / machine / org project

**New personal machine or account (global, all agents):**
```bash
curl -fsSL https://raw.githubusercontent.com/thematthiasleitner/skills/main/install.sh | bash
```
(Clones to `~/.claude/skills` if empty, else `git pull --ff-only`.) Manual equivalent:
`git clone https://github.com/thematthiasleitner/skills.git ~/.claude/skills`.

**Into an org / project ecosystem** (skills travel with the repo so teammates get them):
```bash
cd <the-project-repo>
npx skills add thematthiasleitner/skills --project --copy --all
git add .claude/skills && git commit -m "Add thematthiasleitner skills" && git push
```
`--list` first to preview; `--skill '<name>'` instead of `--all` to inject a subset. This is the
mechanism for "insert into the organisational Claude ecosystem": the org repo carries the skills,
anyone working in it sees them.

---

## Safety invariants

- **Public repo.** Secret scan is non-optional before every `publish`. When in doubt, stop and ask.
- **Never force-push** and **never `git reset --hard`** the canonical repo without explicit consent —
  it's the only copy of skills not yet pushed.
- `publish` writes to a remote → medium-risk: show the diff, propose via AskUserQuestion, don't push
  silently.
- `--copy`, never symlink, when installing — symlinks break once the npx cache is cleared and aren't
  committable.

## Composes with

- `write-a-skill` — create a new skill; then `publish` it everywhere with this skill.
- `session-harvest` — mints skills at session end; `publish` afterward to propagate them.

## Self-evolution

Propose adjustments when: a second skills repo/remote is added (extend the targets table); the user
adopts `gh`/HTTPS as the default push path (swap step 4); a new secret pattern slips through (add it
to `secret_scan.sh`). On approval: edit SKILL.md **and** append to [EVOLUTION.md](EVOLUTION.md).
