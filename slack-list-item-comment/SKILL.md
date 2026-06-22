---
name: slack-list-item-comment
description: Find and post a comment on a Slack List item — routing the comment to the list's discussion channel, NOT to a mirror / log channel that bot-reflects the list. Slack Lists hide each item's comment thread inside a workspace channel whose name is usually `#FC:F<list-file-id>:<list-title>`; finding the right thread is non-obvious. Invoke whenever the user says "comment on this item", "post to the item comments", "reply on the list item", or asks to leave a message tied to a list record.
---

# Slack List Item Comment — Generic Recipe

Slack Lists items each have a discussion thread. The thread does NOT live in the channel where the user normally interacts with the list. It lives in a separate, often hidden, channel that backs the list. Many workspaces also mirror the list into a `#…-log` channel via a bot — **do not post comments there**. Mirror channels are read-only reflections; replies you post there will not appear as item comments.

This skill prevents the most common mistake: posting to the mirror instead of the actual list-item comment thread.

---

## ✋ Pre-flight assertion — run before EVERY `slack_send_message`

This mistake has recurred even with the recipe written down, because agents
*improvise the target* instead of resolving it. Before you post, verify ALL
three or STOP:

1. **`channel_id` is the DISCUSSION channel** — name pattern `#FC:F…:…`
   (cigev Task Dashboard = `C0ABTMRTU9X`). It is **NOT** the `#…-log` mirror
   (cigev = `C0B4V8MVC23`). If your `channel_id` is the mirror, you are wrong —
   full stop.
2. **`thread_ts` parent is a Slackbot `"A comment was added"` message** — NOT a
   bot field-change post containing `["Col…"]`, a `record_id`, a status, or the
   item title. Those `["Col…"]` posts live in the mirror and are changelog
   artefacts; threading a reply under one does NOT create an item comment.
3. **You `slack_read_thread` the candidate root first** and its replies match
   the item's topic. Bare `"A comment was added"` stub + on-topic replies = right
   thread. A `["Col…"]` parent, or replies about a different item = wrong target.

If any check fails, re-resolve with the recipe below. Never "post anyway."

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

## Fast path (one shot) — when the item already has ≥1 comment

You usually don't need to find the discussion channel first. Search a
**unique quoted snippet of an existing comment across ALL channels** (no
`in:` filter) — the hit returns the discussion channel + `thread_ts` together:

```
slack_search_public_and_private  query='"<unique phrase from an existing comment>"'
→ Channel: #FC:F<list-id>:<title> (C…)   thread_ts=…   (also in the Permalink)
```

That single call resolves both the channel and the thread root; jump straight
to **Posting the comment** (verify with `slack_read_thread` if the match is
fuzzy). Use the slower channel-discovery recipe below only when the item has
**zero** comments yet, or the snippet search is ambiguous.

> ⚠️ Plain `slack_search_public` does NOT index Slack List comments — you must
> use `slack_search_public_and_private`. This is the single most common reason
> a comment thread "can't be found".

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

4. **If no existing reply exists** (the item has zero comments yet), OR the
   snippet search returns ONLY mirror hits (common — Slack List comment *text*
   is often not full-text-indexed in the discussion channel; the stub
   `"A comment was added"` carries no text and `slack_read_thread` on it shows
   "No thread messages"), you cannot find the parent by content. Fall back to
   **time-proximity, disambiguated by the mirror's UTC field**:
   - The mirror post for your `record_id` prints the comment's exact wall-clock,
     e.g. `June 15th, 2026 at 6:58 AM UTC` (this is the source of truth for *when*).
   - Read the discussion channel across the item's comment window:
     ```
     slack_read_channel  channel_id="<discussion channel>"  oldest=<UTC-1min>  latest=<UTC+window>
     ```
   - Several `"A comment was added"` stubs usually sit in that window (one per
     comment, across DIFFERENT items). **Pick the stub whose wall-clock matches
     your mirror UTC** (convert: the channel prints local, e.g. CEST = UTC+2, so
     `6:58 UTC` ⇒ a `08:58:xx CEST` stub). Confirm by **elimination** — the
     neighbouring stubs should map to OTHER items' mirror comments at THEIR
     times. Only then reply under the matched stub.
   - A reply posted to the right stub appears in the item's Comments panel even
     when the stub had zero prior replies.

5. **Brand-new item, never commented (no content + no obvious stub).** A freshly
   created item often still has a zero-reply `"A comment was added"` stub from
   around its **creation** time — so when there's no comment-event in the mirror
   to anchor on, time-proximity to the item's *creation* timestamp can still find
   it. If you can't confidently resolve it, the cheapest reliable path is to **ask
   the user to add any one-word comment on the item in the Slack UI** (e.g.
   "seed"). That creates/surfaces the thread and gives you the parent `thread_ts`
   (it's in the permalink of their reply: `…?thread_ts=<parent>&cid=<C…>`); then
   thread your real comment under that parent. The available MCP tools can only
   **reply** to a thread, never originate an item's first comment from nothing —
   so a one-time UI seed (by anyone) is the unblock, not a workaround to force.
   (Verified 2026-06-18 on a fresh Task Dashboard item: user seeded "seed", its
   permalink exposed `thread_ts`, the full comment threaded under it and rendered
   in the item's Comments panel.)

---

## Message structure — two parts, always

Every comment posted to an item thread has **two parts**, in this order:

1. **Human part (first).** Written for a non-technical colleague (e.g. Melanie,
   Nina, Cassandra) to read at a glance. Plain language, no file names, no code
   symbols, no commit hashes. What changed, what it means for them, and whether
   anything is needed from their side. A few sentences max.
2. **Agent part (second).** Written for the next agent/maintainer picking up the
   item. Here you DO name the technical detail: files, functions/symbols, MR /
   commit / deploy-tag IDs, Qualtrics QIDs, Layer C checks, and any constraints
   or gotchas worth carrying forward. Reference code by symbol, not line number
   (line numbers drift).

Separate the two parts clearly — a divider line and a small italic header for the
second part — so the human can stop reading after part 1. Skeleton:

```
<plain-language update for colleagues — what changed + what they need to do>

---
*For the record (technical):*
<files / symbols / MR + deploy IDs / constraints for the next agent>
```

Keep the human part first and skimmable; the agent part can be longer. Don't put
secrets (tokens, internal infra) here — leave those in memory/repo.

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

This has now been corrected **three times** (2026-05-26, and again 2026-06-08).
The recurring failure: an agent posts a status update into the `#…-log` mirror
channel, threading the reply under a `["Col…"]` field-change bot message, and
believes it lands as a list-item comment. It does not. Both channels mention the
same `Rec…` record_id — the mirror via bot reflection, the discussion channel via
the slack-rendered thread — which is the source of the confusion. Only the
discussion channel (name pattern `#FC:F…:…`, cigev = `C0ABTMRTU9X`) is the
canonical home of item comments. The 2026-06-08 repeat happened because the agent
acted from the mirror's search results without invoking this skill — hence the
Pre-flight assertion at the top: **assert the channel before every post.**

---

## Composes with / per-workspace cheat-sheets

This skill is workspace-agnostic — it resolves the discussion channel + thread
at runtime. For a specific recurring list, cache its IDs in a memory or note so
you skip discovery:

- **cigev ADVANCE "Task Dashboard"** (`F0ABTMRTU9X`): discussion channel
  `C0ABTMRTU9X`, read-only mirror `#task-dashboard-log` `C0B4V8MVC23`. See
  memory `reference_task_dashboard_slack`.
- Other lists: drop a one-line `<list-title> → discussion C…, mirror C…` note
  the first time you resolve them.

Pairs naturally with any skill that produces something to *report on* a task
item — e.g. after a deploy, a pipeline summary, or a status update, use this
skill to land the write-up in the right item's Comments thread (deliver a
canvas/file link rather than a wall of text).
