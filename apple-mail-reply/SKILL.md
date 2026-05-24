---
name: apple-mail-reply
description: Compose a reply or a new outgoing message in Apple Mail (via AppleScript), with attachments, in a way that survives Mail's quirks. Two modes — `reply` (find by subject substring, open native reply with recipients + quoted text, body placed on clipboard for user paste) and `new` (explicit To/Cc/subject/body). Always leaves the compose window VISIBLE — never programmatically saves or sends, because programmatic saves on this Mail setup misroute to Trash. Invoke when the user wants to send a reply to a thread in their Apple Mail UNIGE mailbox (or any other configured account) and wants the body + attachments staged for a one-keystroke send.
---

# apple-mail-reply

Wraps Apple Mail compose in a reliable AppleScript flow that avoids three pitfalls observed today (2026-05-23):

1. **`reply origMsg opening yes with reply to all` is a syntax error.** Correct form: `reply origMsg with opening window and reply to all`.
2. **Programmatic `set content to ...` on a reply doesn't survive `save`** — the HTML body wins and the saved draft has empty plain-text content. Workaround: this skill places the body on the macOS clipboard so the user pastes it (⌘V) into the open compose window; the native quoted text is preserved.
3. **Programmatic `save` of a new outgoing message can drop the message into `Éléments supprimés` (Trash)** instead of `Brouillons` (Drafts). Cause unknown (suspected Mail/server sync race). Workaround: NEVER programmatically save or send. Leave the window visible; the user presses ⌘-S (save as draft) or ⌘-⇧-D (send) themselves.

## When to invoke

- User typed `/apple-mail-reply` or asked "compose a reply / new email in Apple Mail to <recipient> about <subject>".
- User wants to attach files from disk to an email that goes through Apple Mail (not Outlook / Microsoft Graph).
- Anything involving the UNIGE mailbox via the local Mail.app UI.

DO NOT invoke for the ADVANCE shared mailbox `advance-project@unige.ch` automation — that goes through Microsoft Graph in `email_draft_automation/` and has its own paths. This skill is the maintainer's *personal* mailbox automation.

## Invocation

### Reply mode

Find the newest message in the account's inbox whose subject contains the substring, open a native reply window (preserves recipients + quoted text), and put the prepared body on the clipboard:

```bash
python ~/.claude/skills/apple-mail-reply/compose_reply.py reply \
  --subject "ADVANCE - Documents for the german translation" \
  --body "Hi Pieter,\n\nPlease find attached: ..." \
  --attach /path/to/file1.json /path/to/file2.docx \
  [--account UNIGE] [--no-cc]
```

Flags:
- `--subject` (required) — case-sensitive substring match on subject.
- `--body` (required) — multi-line plain text; placed on clipboard. Use `\n` for newlines.
- `--attach` (zero or more) — absolute or relative paths; resolved + validated.
- `--account` (default `UNIGE`) — Mail account name (must match Mail's account list).
- `--no-cc` — reply to sender only instead of reply-all (default is reply-all).

After the command returns: switch to Mail (the compose window is foregrounded). **Click in the body above the quoted text and ⌘V** to paste the prepared body. Verify To/Cc + attachments. ⌘-S to save as draft or ⌘-⇧-D to send.

### New-message mode

```bash
python ~/.claude/skills/apple-mail-reply/compose_reply.py new \
  --to pieter@ippo.nl \
  --cc Melanie.Mack@unige.ch \
  --subject "Re: ADVANCE - Documents for the german translation" \
  --body "Hi Pieter, ..." \
  --attach /path/to/file.json \
  [--account UNIGE]
```

For new messages the body is set directly in the compose window (no clipboard needed) since there is no competing native HTML quoted-reply to clobber it. To/Cc/subject/body/attachments all land in one shot.

### What the skill prints

```
OK | matched 4 message(s); using newest from Pieter Overbeeke <pieter@ippo.nl> at <date>

Body has been copied to the clipboard. Switch to the open compose
window, click in the body above the quoted text, and ⌘V to paste.
Attachments added: 3

The compose window is visible. Review, then ⌘-S to save as draft or ⌘-⇧-D to send.
```

## Hard constraints (encoded in the helper)

1. **Never programmatic save.** Programmatic `save` lands in Trash on this setup. Leave the window visible.
2. **Never programmatic send.** Sending is the user's call. The skill won't even offer that option.
3. **Don't silently modify recipients in reply mode.** Mail's native `reply ... with reply to all` chooses To/Cc; don't second-guess it. `--no-cc` exists if you want sender-only.
4. **Attachment paths are absolute.** Helper resolves with `Path.resolve()` and fails if the file doesn't exist.
5. **Account-name fallback.** Default account is "UNIGE"; override with `--account`. Mailbox names are localized (`Boîte de réception` / `Inbox` / `Posteingang`); the helper tries known names in order. If your account uses something else, override the constants at the top of the script.

## When to suggest this skill proactively

If the user is in the translation workflow and is about to send a deliverable to a collaborator (Pieter, Melanie, Theresa), this is the right path. The audit-hardcoded-drafts and refine-drafts skills are for the `advance-project@unige.ch` Microsoft Graph automation — different surface, don't conflate.

## Workflow when invoking

1. Confirm the email contents with the user **before** invoking the helper. Specifically:
   - Show the proposed body verbatim.
   - List the attachment paths + sizes.
   - State the search-subject and expected recipient(s).
   - Confirm reply vs new.
2. Invoke the helper.
3. After helper returns success, tell the user **explicitly**: "The compose window is open in Mail. For reply mode: ⌘V to paste the body, then ⌘-S to save or ⌘-⇧-D to send. For new-message mode: review and ⌘-S / ⌘-⇧-D."
4. DO NOT verify the draft programmatically afterwards (reading `Brouillons` may show empty body or the message may be in Trash — both are false negatives because the user hasn't pressed ⌘-S yet). Trust the user to confirm.

## Common pitfalls (the ones today)

- **HTML reply body clobber**: do NOT use `set content to ...` on a reply message. The clipboard workaround is the only reliable path.
- **Programmatic save misroute**: do NOT call `save` on outgoing messages programmatically. Period.
- **French mailbox names**: `Brouillons` not `Drafts`, `Boîte de réception` not `Inbox`, `Éléments supprimés` not `Deleted Items`. The fallback list in the helper covers FR/EN/DE.
- **Account vs mailbox**: `account "UNIGE"` ≠ `mailbox "UNIGE"`. The hierarchy is `account → mailboxes → messages`.

## File layout

```
~/.claude/skills/apple-mail-reply/
├── SKILL.md
└── compose_reply.py
```

## Cross-references

- AppleScript `Mail` dictionary: open `Mail.app` → File → Open Dictionary if you need to look up other commands.
- Email automation (DIFFERENT — Microsoft Graph, shared mailbox): `email_draft_automation/`. Don't conflate.
- Other related skills: `refine-drafts`, `audit-hardcoded-drafts` (both operate on the Graph mailbox, not Apple Mail).
