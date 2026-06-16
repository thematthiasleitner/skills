---
name: advance-deploy
description: BREAK-GLASS manual deploy to the ADVANCE production server. As of 2026-06-08 (Phase 3, ADR 0004) the NORMAL deploy is automatic — open MR → green CI → push a `deploy-<date>` tag → the server auto-pulls it at its next 15-min cycle (no SSH, no passphrase). Use THIS skill only when auto-deploy is unavailable (paused cycle, broken launcher) or an urgent hotfix can't wait for a cycle: it loads SSH keys via askpass, pushes to GitLab, SSH-pulls on leitneruser@10.40.41.88, then runs Layer C live-Qualtrics verification. **High-risk (push to production is hard to revert) — propose via AskUserQuestion, NEVER silently invoke; explicit consent required.** Prefer the tag-promote path first; surface this only when the user explicitly wants a manual/break-glass deploy.
tools: Bash, Read
---

# ADVANCE Deploy Skill

You deploy the local branch to the ADVANCE production server via the
authenticated commit → push → server-pull → verify dance. This codifies the
multi-step SSH-agent + askpass routine that's needed because the SSH key is
passphrase-protected AND the server-side agent doesn't survive across sessions.

**This skill pushes to production — high-risk.**

## Primary path (try this FIRST — this skill is break-glass)

As of 2026-06-08 the server auto-deploys the latest **promote tag** at the start
of each 15-min cycle (Phase 3; `run/cycle_launcher.sh` + a read-only deploy key;
see `docs/adr/0004-isolated-clones-protected-main-deploy.md` +
`docs/deploy_server_autopull_runbook.md`). The normal deploy is:

```bash
# from your isolated clone, after the change is merged to main via MR + green CI:
git tag deploy-$(date +%F) origin/main && git push origin deploy-$(date +%F)
# the server checks out this tag within ~15 min — no SSH, no passphrase.
```

Only fall through to the manual dance below when auto-deploy is **paused/broken**
or an **urgent hotfix** can't wait for a cycle. Confirm with the user that they
want a manual break-glass deploy before proceeding.

**Discovery vs invocation pattern** (per project CLAUDE.md "Skill-suggestion checkpoint"):

- ✅ **DO surface this skill via `AskUserQuestion`** whenever the user is in a
  context where deploying would help (has unpushed commits + a clean tree,
  mentions wanting to deploy/ship/release/push). State what would be
  pushed (commit subject lines) so the user can decide informed.
- ❌ **NEVER silently invoke** without explicit consent. Pushes are hard to
  revert and visible to all teammates.
- ✅ **If the user types `/advance-deploy`** or explicitly approves the
  AskUserQuestion proposal, that IS explicit consent — proceed.

The AskUserQuestion proposal should:
- List the commits that would be pushed (1-line subjects)
- Note the side effects ("push to origin/main + server pull + Layer C verify")
- Offer at least one alternative ("alternatively: commit but don't deploy yet")

**Composability:** typically runs after `/qualtrics-restructure-step` + manual
`--apply`, or after any code change. Followed by `/qualtrics-e2e-pressure-test`
or `/advance-server-cycle-trigger` to verify the deployed change works.

---

## When to propose (then await explicit consent)

User has committed local changes and wants them on the production server.
Typical sequence:
- Edits + commits done locally
- **Propose `/advance-deploy` via AskUserQuestion** ← you are here
- On consent: deploy + Layer C verifies on server against live Qualtrics
- (optional) propose `/qualtrics-e2e-pressure-test` for survey changes

## When NOT to propose

- If there are uncommitted changes in the working tree — propose committing
  first (or `git stash` if user wants to defer them).
- For surveys-only changes — propose `/qualtrics-restructure-step` + `--apply`
  directly. Those don't touch the codebase, so no deploy needed.
- If `git log origin/main..HEAD` is empty — nothing to deploy; don't propose.

## When to invoke directly (no AskUserQuestion needed)

- The user typed `/advance-deploy` in the chat — explicit consent
- The user already approved a multi-step plan that included a deploy step

---

## Deploy modes (pick before Step 0)

- **Full (default):** `git push origin main` → server `git pull origin main`.
  Use when `main` is healthy and everything on it is meant to ship.
- **Single-commit / feature-branch:** when `main` carries ANOTHER agent's
  unreleased or test-red commits and you must ship ONLY your change, do NOT pull
  `main` HEAD onto the server. Instead:
  - integrate your commit so it isn't lost — fetch, then fast-forward `main` to it
    (or rebase your commit onto `origin/main`) and push; **and**
  - on the server, fast-forward to YOUR specific commit, not `main` HEAD:
    `git fetch origin && git merge --ff-only <your-sha>` (server ends one commit
    behind `origin/main`, carrying only your delta on top of what's already live).
  Always verify the deployed file actually contains your change (`grep` a marker) —
  a failed server fetch silently leaves HEAD unmoved ("Already up to date").
  ⚠️ First check the server's CURRENT HEAD: if your "green base" is BEHIND the live
  HEAD, a plain checkout would ROLL BACK another agent's already-live work.

## Workflow

### Step 0: Pre-deploy checks

```bash
cd email_draft_automation
git status -s     # warn user if uncommitted changes
git log origin/main..HEAD --oneline   # show what will be pushed
```

Refuse to proceed if:
- Working tree has uncommitted changes the user hasn't acknowledged
- HEAD is BEHIND origin/main (would push a rewrite — needs manual handling)

### Step 1: Get the passphrase (single-line input, never persist)

Ask the user to paste the SSH passphrase (the SAME one that unlocks
`~/.ssh/gitlab_unige` + `~/.ssh/ssh-key` + sudo on the server).

NEVER write it to a config file, NEVER echo it back, NEVER include it in
a commit message or log. Use the BASH local var pattern below.

### Step 2: Load keys + push + pull

Use [_deploy.sh](_deploy.sh) (in this skill folder) to execute the full
dance in one go. The script:
- Writes a transient askpass shell script to /tmp (700 perms, shredded after)
- ssh-adds the gitlab + ssh-key keys to the agent
- `git push origin main`
- ssh to server, runs the SAME askpass dance there to add the server-side
  gitlab key + pull
- Shreds all askpass scripts

The script takes the passphrase via stdin (NOT command-line arg, NOT env var)
so it doesn't show up in `ps aux` or shell history.

```bash
echo "$PASS" | bash ~/.claude/skills/advance-deploy/_deploy.sh
```

#### Step 2 ALT: passphrase-free server pull via forwarded agent (no server-side gitlab passphrase)

If `~/.ssh/ssh-key` + `~/.ssh/gitlab_unige` are already loaded in your LOCAL agent
(e.g. you ran `ssh-add` yourself, or `request-ssh-access`), you can skip the
server-side askpass entirely: forward your agent and override the server's
`IdentitiesOnly` so the server's `git` authenticates to GitLab with YOUR forwarded
gitlab key. Local `git push origin main` works with the loaded key; then:

```bash
ssh -A -o ControlPath=none -i ~/.ssh/ssh-key -o IdentitiesOnly=yes leitneruser@10.40.41.88 '
  cd ~/email_draft_automation &&
  GIT_SSH_COMMAND="ssh -o IdentitiesOnly=no -o IdentityAgent=$SSH_AUTH_SOCK" git fetch origin &&
  git merge --ff-only origin/main'   # or: --ff-only <your-sha> for single-commit mode
```

⚠️ **ControlMaster gotcha:** if `advance-agent-session` warmed a ControlMaster for
the server, it was opened WITHOUT `-A`, and a *reused* master connection has no
agent forwarding → the forwarded fetch fails ("correct access rights"). The
`-o ControlPath=none` above forces a FRESH forwarded connection just for the pull,
bypassing the (forwarding-less) master. The guard's own lock-check still rides the
warm master. This is the route that worked on 2026-06-04 when the server had no
SSH agent and couldn't reach GitLab on its own.

(Note: the server-side `sudo` for pausing the cycle still needs the real
passphrase — forwarding doesn't help there.)

### Step 3: Server-side Layer C verify

After the pull succeeds, run Layer C on the server against LIVE Qualtrics +
LIVE workbook:

```bash
ssh leitneruser@10.40.41.88 'cd ~/email_draft_automation && \
  set -a && source qualtrics/qualtrics_env.sh && set +a && \
  unset QUALTRICS_WORKBOOK_PATH && QUALTRICS_WORKBOOK_MODE=live \
  .venv/bin/python3 tools/layer_c_smoke.py --quick --skip calendar-dry-run'
```

Parse output: count PASS/FAIL/SKIP. If ANY FAIL, surface the FAIL detail
and refuse to declare deploy success.

### Step 4: Report

Pretty-print:
- Commits pushed (sha + first line of message)
- Server pull diff stats (files changed, insertions/deletions)
- Layer C summary line + any FAIL detail

---

## Safety invariants

- **Passphrase is ephemeral.** Never log, echo, persist, or include in
  commit message. The askpass script lives ≤2s in /tmp before shred.
- **Never `git add -A` or `git add .`.** Stage only files the user names
  explicitly (or honor `git diff --staged` if they staged manually).
- **Never `--no-verify`, `--no-gpg-sign`, `--amend`** unless the user
  explicitly requested it.
- **Refuse force-push.** `git push -f` requires re-prompt with explicit
  consent + reason.
- **Refuse to push if Layer A is red.** Always run `make test-a` before
  pushing (unless the user explicitly waived it — and document why).
- **Refuse to push if server is in manual-mode** (server-guard hook
  bypassed). Check via `reference-manual-cycle-control` pattern and warn
  the user to complete the manual maintenance first.

## On red (Layer C FAIL on server post-pull)

- Do NOT roll back automatically. Surface the FAIL detail to the user.
- Document the likely cause (typically: a code change that's incompatible
  with current live Qualtrics state, OR a Qualtrics-side change that the
  Layer C check happens to detect for the first time).
- Suggest next steps: investigate the FAIL detail in journalctl OR roll
  back via `git revert` (the user decides which).

## Composes with

- `/qualtrics-restructure-step` — typically what produced the change being deployed
- `/qualtrics-e2e-pressure-test` — verify the deployed survey change end-to-end
- `/advance-server-cycle-trigger` — force an immediate cycle to materialize
  changes into the live workbook
