---
name: git-push
description: Push the current branch to its remote, handling SSH passphrase authentication automatically. Detects which SSH key to use based on the remote URL (github.com → ssh-key, gitlab → gitlab_unige), checks whether the key is already loaded in ssh-agent, and only asks for the passphrase when actually needed. **Propose via AskUserQuestion when the user says "push", "git push", "push to remote", or after a commit.** Medium-risk (writes to remote) — always show what will be pushed before doing it.
tools: Bash, AskUserQuestion
---

# git-push

Handles git push with SSH passphrase authentication.

## Key map

| Remote host | Key file |
|---|---|
| `github.com` | `~/.ssh/ssh-key` |
| `gitlab` / `unige` | `~/.ssh/gitlab_unige` |

## Workflow

### Step 1: Situational awareness

```bash
# Current repo, branch, remote, upstream
git remote -v
git status --short --branch
git log @{u}..HEAD --oneline 2>/dev/null || git log --oneline -5
```

Show the user: remote URL, current branch, commits that will be pushed. Stop and report if working tree is dirty (unstaged changes) or if there's nothing to push.

### Step 2: Check if SSH key is already loaded

```bash
ssh-add -l 2>/dev/null
```

- If the relevant key fingerprint appears → skip to Step 4 (push directly).
- If `The agent has no identities` or key is absent → Step 3.
- If `Could not open a connection to your authentication agent` → start agent first:

```bash
eval "$(ssh-agent -s)"
```

### Step 3: Ask for passphrase (only if key not loaded)

Use AskUserQuestion to ask for the passphrase. Inform the user:
- Which key will be loaded (`~/.ssh/ssh-key` or `~/.ssh/gitlab_unige`)
- That the passphrase will appear in the conversation
- That it will stay cached in ssh-agent for the rest of the session (no need to enter it again)

Then load the key:

```bash
bash ~/.claude/skills/git-push/_load_key.sh "$KEY_PATH" "$PASSPHRASE"
```

If `ssh-add` fails (wrong passphrase) → report and stop. Do NOT retry automatically; ask the user to re-invoke.

### Step 4: Push

```bash
git push                          # if upstream is set
git push -u origin HEAD           # if no upstream yet
```

Show the full output. If push is rejected (non-fast-forward), report it and suggest `git pull --rebase` — do NOT force-push without explicit user instruction.

### Step 5: Confirm

```bash
git log @{u}..HEAD --oneline
```

Should return empty (all commits pushed). Report success or any remaining commits.

---

## Safety invariants

- **Never force-push** (`--force`, `--force-with-lease`) unless the user explicitly asks.
- **Never push to main/master** without confirming with the user first.
- **Never store the passphrase** anywhere — it lives only in the Bash call and then in ssh-agent memory.
- If the remote is unfamiliar (not github.com or a known gitlab host), pause and confirm with the user before pushing.

---

## Self-evolution

Propose adjustments when:

- A new SSH key / host mapping is needed → add a row to the key map table.
- The user keeps pushing with `--force-with-lease` → add a named workflow step for it.
- The user's ssh-agent setup differs (e.g. 1Password SSH agent, Secretive) → adapt the agent-start step.

On approval: edit SKILL.md AND append to [EVOLUTION.md](EVOLUTION.md).

## Composes with

- `/obsidian-plugin-deploy` — deploy runs after push for Obsidian plugins.
- `/advance-deploy` — ADVANCE project deployment.
