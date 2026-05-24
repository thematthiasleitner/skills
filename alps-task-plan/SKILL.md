---
name: alps-task-plan
description: Reads an ALPS Slack List task record and produces a step-by-step action plan with owners, blockers, and what Claude can do immediately. Use when user pastes an alps-foundation.slack.com/lists/ URL and asks for a plan, next steps, or how to accomplish a task.
---

# ALPS Task Plan

## Quick start

User gives: `https://alps-foundation.slack.com/lists/T049Q4TS0TX/F0B2VQWTKM5?record_id=RecXXXXXXXX`

Run the workflow below. Output: task summary + actionable plan.

## Workflow

### 1. Extract record_id
Parse `record_id=` from URL query string.

### 2. Fetch task state
`slack_search_public_and_private` query: `<record_id>` — finds full audit trail from #task-list-log (channel C0B4BAW6YNB). Latest entry = current state: name, description, assignees, status, channel, priority, due date.

### 3. Read task list metadata
`slack_read_file` file_id: `F0B2VQWTKM5` — CSV with all tasks. Cross-reference to confirm current values.

### 4. Read linked channel context
`slack_read_channel` on the channel(s) listed in the task. Limit 30 msgs. Look for: existing work, canvases, docs, open questions.

### 5. Search for existing work
`slack_search_public_and_private` query: `<task name keywords>` — find canvases, Drive links, prior discussion.

### 6. Output plan

```
## Task: [Name]
**Status:** [status] | **Assignees:** [names] | **Priority:** [priority] | **Due:** [date or —]

**Description:** [from task]

---
### What exists
- [list existing work / docs / canvases found]

### Blockers
- [missing data, waiting on person, unclear ownership]

### Plan
1. [Step] → Owner: [name]
2. ...

### Claude can do now
- [concrete actions: draft, search, reconcile, summarize]
```

## Notes
- Task list file ID: `F0B2VQWTKM5` (ALPS Task List, workspace T049Q4TS0TX)
- Task log channel: `C0B4BAW6YNB` (#task-list-log)
- Always use latest log entry for current state — earlier entries show edit history
- If description empty in log, check CSV for fuller text
