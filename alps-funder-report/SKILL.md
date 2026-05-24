---
name: alps-funder-report
description: Drafts and updates funder-facing impact and finance report sections for ALPS events (Summer School, Conference, etc.) using bank-reconciled accounting data from Slack canvases and Google Drive. Use when user asks to draft, write, or update a funder report, impact report, or finance section for an ALPS event, or mentions ERNA, grant report, or fund provider report.
---

# ALPS Funder Report

## Quick start

User says: "draft the finance section for [event]" or "update the ASS25 funder report"

Run workflow below. Output: clean markdown finance section ready to paste into report doc.

## Workflow

### 1. Find accounting canvas
`slack_search_public_and_private` query: `[event] accounting bank reconciliation canvas`
→ Read canvas with `slack_read_file` or `slack_read_canvas`
→ Extract: final net surplus, income breakdown, expense breakdown, budget v actual

### 2. Read existing draft (if provided)
If user gives Google Doc link → `mcp__f5357a15__read_file_content` with file_id from URL
If restricted → note it, work from Slack context instead

### 3. Gather impact data
`slack_search_public_and_private` queries:
- `[event] participants attendees [year]` → participant count, profile (student/prof/PhD)
- `[event] speakers [year]` → speaker names, topics
- `[event] ERNA grant beneficiaries subsidised` → who received grant-subsidised tickets

### 4. Draft finance section

Structure (always this order):
1. **Overview paragraph** — headline surplus, one sentence on financial health
2. **Income table** — rows: participant fees (n registrations), ERNA grant (if applicable), other grants; Total
3. **Expenses table** — rows: venue, speaker reimbursements, supplies/equipment, other, welcome gifts; Total
4. **Budget vs Actual table** — Budget / Actual / Delta for income, expenses, surplus
5. **ERNA grant usage paragraph** — how grant was used, # beneficiaries (flag if unknown)
6. **Open items** — explicit list of missing data needed before sending

### 5. Output format

```markdown
## Financial Report — [Event] [Year]

### Overview
[2-3 sentences: surplus, financial health, what surplus enables]

### Income
| Source | CHF |
...
| **Total income** | **XX,XXX** |

### Expenses
| Category | CHF |
...
| **Total expenses** | **XX,XXX** |

### Budget vs. Actual
| | Budget | Actual | Delta |
...

### Grant usage — [Funder name]
[Narrative: amount received, how used, # beneficiaries, impact]

### Open items
- [ ] [Missing data point + who can provide it]
```

## Rules
- **Always** use final bank-reconciled figures, not budget projections
- **Always** call out ERNA grant as separate income line (booked as donation acct 3200, not ticket revenue)
- **Always** flag missing data as explicit open items — never fabricate
- Round to nearest CHF in tables; use exact figures in prose for key numbers
- Sources: link to accounting canvas + Drive xlsx at bottom

## Key file IDs (ASS 2025)
- Accounting canvas: `F0B4Q11EZCL` (ASS 2025 Bank Reconciliation — final net +CHF 9,174.90)
- Bank vs Budget xlsx: Drive `1qd7ANvorS_g3TjdAXsAG3LI2qkj-o-3j`
- Budget v4: Google Sheet `1AkQMSIL17Vf0utz4CKt5stZUCgdj5-OTrmmz867Em9E`
- Noor's draft doc: Google Doc `1NfTScyJ_tOmY7QW64fDHJUkvMaXhkD3m` (may be restricted)
