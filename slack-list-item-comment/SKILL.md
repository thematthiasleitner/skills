---
name: slack-list-item-comment
description: Find and post a comment on a Slack List item — routing the comment to the list's discussion channel, NOT to a mirror / log channel that bot-reflects the list. Slack Lists hide each item's comment thread inside a workspace channel whose name is usually `#FC:F<list-file-id>:<list-title>`; finding the right thread is non-obvious. Invoke whenever the user says "comment on this item", "post to the item comments", "reply on the list item", or asks to leave a message tied to a list record.
---

# Slack List Item Comment — Generic Recipe

Slack Lists items each have a discussion thread. The thread does NOT live in the channel where the user normally interacts with the list. It lives in a separate, often hidden, channel that backs the list. Many workspaces also mirror the list into a `#…-log` channel via a bot — **do not post comments there**. Mirror channels are read-only reflections; replies you post there will not appear as item comments.

This skill prevents the most common mistake: posting to the mirror instead of the actual list-item comment thread.

---

## The two channels you must distinguish

| Channel | Identifier pattern | Role | Post here? |
|---|---|---|---|
| **List discussion channel** | Name usually `#FC:F<list-file-id>:<list-title>` (e.g. `#FC:F0ABTMRTU9X:Task Dashboard`). Type: regular channel; ID starts with `C…`. | Hosts each item's comment thread. Each item has a Slackbot parent message `"A comment was added"` + its replies. | **YES** |
| **Mirror / log channel (if exists)** | User-named, e.g. `#task-dashboard-log`. A bot posts a new message any time a list column changes (title, status, comments). | Read-only reflection of column updates. Bot messages here are NOT the item comment thread. | **NO** |

If you can't tell which is which:
- The mirror channel has bot posts that contain field metadata (record_id, column id like `Col…`, title, status, etc.) — usually one message per column change.
- The discussion channel has Slackbot messages with the literal text `"A comment was added"` as thread parents, with human replies underneath.

---

## How to find the discussion channel for a given list

You usually know one of these starting points:

1. **You know the list's File ID** (`F…`, visible in the list URL `slack.com/lists/T…/F…?…`):
   - Search channels for the file ID: `slack_search_channels  query="F<id>"` — sometimes returns the discussion channel by name.
   - Or search messages for the file ID across all channels and look at the channel they live in.

2. **You don't know anything but the list title**:
   - `slack_search_channels  query="<list title fragment>"  channel_types="public_channel,private_channel"`.
   - The channel whose name starts with `FC:F` is the discussion channel.

3. **Fallback**: search for a recent comment you already know was made on the list. Filter by author and content; the channel it lives in is the discussion channel.

Cache the channel ID once found — you don't need to re-discover it per session.

---

## How to find the thread parent for a specific item

The trick: thread parents are Slackbot messages whose text is literally `"A comment was added"`. They are uninformative on their own. You have to find them by their **thread content** (an existing reply mentioning the item's topic), since the parent itself has no identifying text.

Recipe:

1. **Identify the item** — get its record_id (`Rec…`) from the mirror channel, the list URL, or the user's description.

2. **Search the discussion channel for an existing reply** matching the item's topic:
   ```
   slack_search_public_and_private  query="<distinctive phrase from the item> in:<#C…discussion channel>"
   ```
   Each hit comes with a `thread_ts` attribute pointing at the parent Slackbot message.

3. **Verify with `slack_read_thread`** on `channel_id=<discussion channel>, message_ts=<thread_ts>`. The replies should clearly correspond to the item.

4. **If no existing reply exists** (the item has zero comments yet), you cannot find the thread parent by content. Fall back to time-proximity:
   - Note the item's creation timestamp (visible in the mirror channel or the list).
   - Read the discussion channel near that timestamp:
     ```
     slack_read_channel  channel_id="<discussion channel>"  oldest=<just before>  latest=<just after>
     ```
   - The Slackbot `"A comment was added"` message closest to the item's creation time is the parent. Confirm before posting.

---

## Posting the comment

Once you have `thread_ts`:

```
slack_send_message
  channel_id="<discussion channel C…>"
  thread_ts="<parent ts>"
  message="<your comment, markdown allowed>"
```

The reply appears in the item's Comments panel in the Slack List UI.

---

## Tagging users

To tag a user: find their user_id with `slack_search_users  query="<full name>"` and use `<@U…>` syntax in the message body.

---

## Drafts vs send

The Slack toolkit has both `slack_send_message` and `slack_send_message_draft`. For visible-to-others actions, prefer drafting first **unless the user has explicitly authorized sending** ("send the comment", "post it", "comment on this item"). If they only say "write a comment", draft don't send.

---

## What NOT to do

- ❌ Post a thread reply on a bot message in the mirror / log channel. Those bot messages are mirror artefacts of column updates — they are not the item's comment thread, and the user will not see replies there as item comments.
- ❌ Post a top-level message in the mirror channel tagging colleagues. Same reason.
- ❌ Try to update the item's "Description" or "Comments" column via channel messages — that's not how Slack Lists work. Comments are stored as thread replies in the discussion channel.
- ❌ Assume there's a `lists.items.update` MCP tool available. Standard Slack MCP toolkits don't expose the Lists API directly; only the channel-thread approach works.

---

## Reference incident

A previous session posted a long status update to a `#…-log` mirror channel thread, mistakenly believing it would surface as a comment on the corresponding list item. The user had to correct twice. The root confusion was that BOTH channels mention the same `Rec…` record_id — the mirror via bot reflection, the discussion channel via the slack-rendered thread. Only the discussion channel (whose name pattern is `#FC:F…:…`) is the canonical home of item comments.
