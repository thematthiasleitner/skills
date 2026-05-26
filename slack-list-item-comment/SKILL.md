---
name: slack-list-item-comment
description: Find and post a comment on a Slack List item in the unige-cal-cigev "Task Dashboard" list. Use whenever the user says "comment on this item", "post to the item comments", "reply on the list item", or asks to leave a message tied to a list record. Routes the comment to the correct underlying channel (`C0ABTMRTU9X`) — NOT to the mirror `#task-dashboard-log` channel.
---

# Slack List Item Comment — ADVANCE Task Dashboard

You are about to post a comment on a Slack **List item**. Read this whole file before sending. The mistake this skill prevents has happened — the user has corrected it. Do not repeat it.

---

## Two channels — DO NOT CONFUSE THEM

| Channel | ID | What lives there | Post here? |
|---|---|---|---|
| **`#FC:F0ABTMRTU9X:Task Dashboard`** | `C0ABTMRTU9X` | The actual comment threads attached to list items. Each item has one thread parent (a Slackbot message `"A comment was added"`). | **YES — this is where comments belong.** |
| `#task-dashboard-log` | `C0B4V8MVC23` | Read-only mirror: the bot posts a new message any time a list column changes (title, status, comment text, etc.). Threads on these bot messages are unrelated to item comments. | **NO. Never. The user has corrected this twice.** |

**When the user says "comment on this item" / "comment of the item" / "the item comments", they mean the comments panel of the item in the Slack List UI — which lives in `C0ABTMRTU9X`. Not the dashboard log.**

---

## How to find the right thread parent for an item

The trick: thread parents are Slackbot messages whose text is just `"A comment was added"`. They are uninformative on their own. You have to find them by their thread *content* (existing replies on the item), since the parent itself has no topic.

Recipe:

1. **Find the item's record_id** by searching for the title in the mirror channel:
   ```
   slack_search_public_and_private  query="<keyword> in:<#C0B4V8MVC23>"
   ```
   Each bot post contains a `Rec…` record_id. Note it.

2. **Search for related discussion in the comment channel** by topic keywords:
   ```
   slack_search_public_and_private  query="<distinctive phrase> in:<#C0ABTMRTU9X>"
   ```
   - The result will be a Matthias / colleague reply with a `thread_ts` attribute. **That `thread_ts` is the comment thread parent for some item — verify it matches your item by reading the thread.**

3. **Verify with `slack_read_thread`** on `channel_id=C0ABTMRTU9X, message_ts=<thread_ts>`. The reply content should clearly correspond to the item.

4. **If no existing reply exists** (item has zero comments yet), you cannot find the thread parent by content. In that case:
   - Read the channel near the item's creation time:
     `slack_read_channel  channel_id="C0ABTMRTU9X"  oldest=<just before item creation>  latest=<just after>`
   - The Slackbot's `"A comment was added"` message is the parent. Confirm by timestamp proximity to the item creation timestamp (visible in `#task-dashboard-log`).

5. **Post the comment** as a thread reply:
   ```
   slack_send_message
     channel_id="C0ABTMRTU9X"
     thread_ts="<the parent ts you found>"
     message="<your comment, markdown allowed>"
   ```

---

## Tagging users

To tag a user in the comment:

1. Find their Slack user_id with `slack_search_users  query="<full name>"`.
2. Use `<@U…>` syntax in the message body (e.g. `<@U0B31E53RDZ>`).
3. Cached IDs for common ADVANCE people:
   - Agathe Nobis: `U0B31E53RDZ` (agathe.nobis@unige.ch)
   - Melanie Mack: `U07MZSNDUFM` (melanie.mack@unige.ch)
   - Matthias Leitner (the user): `U09G27WLEUV`
   - Verify before using — IDs change rarely but do.

---

## Drafts vs. send

The Slack toolkit has both `slack_send_message` and `slack_send_message_draft`. For visible-to-others actions, prefer drafting first **unless the user has explicitly authorized sending in their request** ("send the comment", "post it", "comment on this item"). If they only say "write a comment", draft don't send.

---

## What NOT to do

- ❌ Post a thread reply on a bot message in `#task-dashboard-log` (`C0B4V8MVC23`). Those bot messages are mirror artifacts of column updates — they are not the item's comment thread, and the user will not see replies there as item comments.
- ❌ Post a top-level message in `#task-dashboard-log` tagging colleagues. Same reason.
- ❌ Try to update the item's "Description" or "Comments" column via channel messages — that's not how Slack Lists work. Comments are stored as the actual thread replies in `C0ABTMRTU9X`.
- ❌ Assume there's a "lists.items.update" MCP tool available — there isn't (as of 2026-05-26). Only the channel-thread approach works.

---

## Quick reference

```
Workspace:       T07KSC3L98D (unige-cal-cigev)
List file:       F0ABTMRTU9X
Comment channel: C0ABTMRTU9X  ← post here
Mirror channel:  C0B4V8MVC23  ← read only; never post
Mirror bot:      B0B4V94HWHM
Item URL:        https://unige-cal-cigev.slack.com/lists/T07KSC3L98D/F0ABTMRTU9X?record_id=<Rec…>
```

When a session involves both reading item state AND commenting on it, keep these two channels mentally separated from the first action: read from `C0B4V8MVC23` (mirror, has the metadata), write to `C0ABTMRTU9X` (comment thread).
