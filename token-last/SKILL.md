---
name: token-last
description: Use whenever you are about to give the user a shell command they must complete with a SECRET they paste in — a token, API key, personal access token, GitLab runner/registration token, bearer token, or password. Formats the command so the secret PLACEHOLDER is the LAST characters on the LAST line, so the user can paste their secret at the very end without arrowing into the middle of the command. Also triggers when the user types /token-last.
---

# token-last

When a command needs the user to supply a secret, make pasting effortless: the
secret goes **last**. The user should be able to click at the end of what you
printed, paste, and run — never edit the middle.

## Rules

1. **Secret = final token on the final line.** Restructure flags/arguments so the
   placeholder is the very last thing. Use trailing-backslash multi-line layout
   and put the secret-bearing flag on its own last line.
2. **Use a loud placeholder** the user can't miss: `PASTE-TOKEN-HERE`,
   `PASTE-glrt-TOKEN-HERE`, `<PASTE-API-KEY>`. Never a vague `XXX` mid-line.
3. **Quote it** (`"PASTE-TOKEN-HERE"`) so pasted secrets with special characters
   don't break the shell.
4. **Never invent or echo a real secret.** Don't print the user's actual token,
   don't read it back, don't `echo $TOKEN`. If a value must be reused, assign it
   to a variable (value last on that line) and reference the variable after.
5. **Say it in one line of prose**: "paste your token at the end."
6. **Multiple secrets:** prefer one `export VAR=PASTE-HERE` line per secret
   (value last), then a command that references `$VAR` — so each line still ends
   in a paste point.

## Patterns

GitLab runner register — token last:
```bash
gitlab-runner register --non-interactive \
  --url "https://gitlab.unige.ch" \
  --executor "shell" \
  --description "my-runner" \
  --token "PASTE-glrt-TOKEN-HERE"
```

curl with a bearer token — auth header last:
```bash
curl https://api.example.com/v1/thing \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer PASTE-TOKEN-HERE"
```

Reused secret via a variable (value last, then reference) — nothing is echoed:
```bash
export GITLAB_TOKEN="PASTE-TOKEN-HERE"
# then, separately:
glab auth login --hostname gitlab.unige.ch --token "$GITLAB_TOKEN"
```

## Anti-patterns (fix these)

- `curl -H "Authorization: Bearer XXX" https://… -H "Accept: …"` → secret buried
  mid-command. Move the auth header to the **last** line.
- `gitlab-runner register --token XXX --url … --executor …` → token first. Move it
  **last**.
- `echo "your token is $TOKEN"` → never echo the secret back.
