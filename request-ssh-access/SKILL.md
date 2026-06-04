---
name: request-ssh-access
description: Standardize how an agent gains use of a passphrase-protected SSH key WITHOUT ever handling the passphrase itself. The agent checks whether the key is loaded in ssh-agent; if not, it asks the user to paste `ssh-add <key>` into their OWN terminal and type the passphrase there, then verifies and proceeds. Use as the "get access first" step BEFORE any operation needing a passphrase-protected key and that key isn't loaded yet — server SSH to leitneruser@10.40.41.88, or git push/pull over SSH to gitlab.unige.ch / github.com. Defaults to ~/.ssh/ssh-key; works for any key (gitlab_unige, github_thematthiasleitner). Composable: other skills (advance-deploy, advance-server-cycle-trigger, git-push) reference it instead of the in-conversation askpass dance.
tools: Bash
---

# request-ssh-access

Load a passphrase-protected SSH key into the **shared** ssh-agent so the agent's `Bash` tool can use it — **without the passphrase ever entering the conversation**. The user types it in their own terminal; the agent only checks, asks, and verifies.

Works because the Claude Code `Bash` tool shares the user's macOS ssh-agent: a key the user `ssh-add`s in Terminal becomes visible to `ssh-add -l` from `Bash`.

## Default key

`~/.ssh/ssh-key` (ADVANCE server login). Override with whatever key the task needs — e.g. `~/.ssh/gitlab_unige`, `~/.ssh/github_thematthiasleitner`.

## Workflow

### Step 1 — Resolve the key + its fingerprint

```bash
KEY="$HOME/.ssh/ssh-key"          # or the key the task needs
ssh-keygen -lf "$KEY.pub"          # target fingerprint (SHA256 ...)
```

### Step 2 — Is it already loaded?

```bash
ssh-add -l 2>&1
```

- Target fingerprint appears → **already loaded. Proceed silently. Do NOT pester the user.**
- `The agent has no identities` / fingerprint absent → Step 3.
- `Could not open a connection to your authentication agent` → no agent in this shell; still go to Step 3 (the user's Terminal has its own agent), then rely on Step 4 to confirm the shared socket actually carries the key.

### Step 3 — Ask the user to load it (they type the passphrase)

Present this **exact** copy-paste block and **stop your turn**, asking the user to run it in their own terminal and enter the passphrase:

```
ssh-add ~/.ssh/ssh-key
```

> Optional (macOS) to persist across reboots via Keychain: `ssh-add --apple-use-keychain ~/.ssh/ssh-key`

Substitute the real key path if not the default. **Hard rules — never violate:**

- ❌ Do NOT attempt the passphrase yourself, write an askpass script, or use `SSH_ASKPASS`.
- ❌ Do NOT ask the user to paste, type, or send the passphrase into the conversation.
- ✅ The passphrase exists only in the user's terminal + ssh-agent memory.

### Step 4 — Verify, then continue

After the user confirms they ran it:

```bash
ssh-add -l 2>&1                    # target fingerprint should now be present
```

- Present → access granted; continue with the original task.
- Still absent → the user's Terminal and the `Bash` tool are using **different** ssh-agents (different `SSH_AUTH_SOCK`). Report this; do not loop. Fall back: have the user run the loading command and the dependent command in the same shell, or troubleshoot the agent socket.

## Safety invariants

- The passphrase **never** appears in the conversation, a file, an env var, or a command.
- Never retry a failed `ssh-add` on the user's behalf — wrong passphrase is theirs to re-enter.
- Idempotent: if the key is already loaded, this skill is a no-op (Step 2 short-circuits).
- This skill grants *use* of a key for the session; it does not add, remove, or modify keys.

## Composes with

Make this the **access precondition** other flows call before SSH/git-over-SSH work:

- `advance-deploy`, `advance-server-cycle-trigger` — run this for `~/.ssh/ssh-key` before SSHing to `leitneruser@10.40.41.88`.
- `git-push` — prefer this over its in-conversation passphrase prompt (Step 3) when the user wants the passphrase to stay out of the chat.

A composing skill should: pick the key its operation needs → run Steps 1–2 → if loaded, proceed; if not, hand off to Step 3 and wait for the user.

## Self-evolution

When a new host/key pairing recurs, note its default key here so callers don't have to guess. If the user adopts a non-default agent (1Password SSH agent, Secretive), adapt Step 2/4's agent assumptions.
