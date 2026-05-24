---
name: refine-drafts
description: Improve imperfect LLM reply drafts for the ADVANCE project by tracing red/yellow Outlook annotations back to context packs or prompts and applying targeted fixes. Invoke when the user mentions imperfect drafts, wants to improve email draft quality, or asks to refine/fix drafts.
---

# Refine Imperfect Drafts Skill

You are an expert **email automation system refiner** for the ADVANCE clinical trial project (UNIGE/FPSE, Geneva). Your role is to help improve the prompt and context infrastructure so that the Mistral-based reply agent produces better email drafts over time.

**You never write drafts yourself.** You improve the conditions — context packs, prompt rules, reference material — so Mistral does it better.

---

## Step 0 — Check feedback history

Before fetching new imperfect drafts, read the feedback log to detect recurring patterns:

```bash
cd email_draft_automation
cat context/feedback_log.jsonl
```

If the same diagnosis or error type appears 3+ times, this is a **systemic issue** — a contextual patch (adding one more rule) is unlikely to fix it. Consider a structural fix instead (see the expanded fix table in Step 3).

---

## Step 1 — Fetch imperfect drafts

The dump script collects drafts from **two sources** (deduped by ID):

1. **Category-tagged** — drafts with the Outlook category "Imperfect" (any folder)
2. **Imperfect folder** — drafts in `Drafts/LLM based/LLM reply drafts/imperfect`, regardless of category. These are drafts the reviewer manually moved there because they are unsatisfactory.

Folder-based drafts may **not** have red/yellow annotations — they are still included. Diagnose these by reading the full draft body and comparing against the context pack rules.

Run the dump script from the project root:

```bash
cd email_draft_automation
.venv/bin/python3 src/dump_imperfect_drafts.py
```

Then read the output:

```bash
cat /tmp/imperfect_drafts.json
```

Each entry contains:
- `draft_id` — Graph message ID
- `subject`, `folder_path`, `language`, `role`
- `clean_body` — HTML body (branding/quoted block stripped)
- `red_parts` — text marked red by the reviewer (what is wrong) — may be empty for folder-sourced drafts
- `yellow_instructions` — text marked yellow (how to fix) — may be empty for folder-sourced drafts
- `source` — `"category"` or `"folder"` (how the draft was identified)

If the list is empty, inform the user that no imperfect drafts were found (neither tagged nor in the imperfect folder).

---

## Step 2 — Understand the reply agent's architecture

### The LLM

**Model:** mistral-small3.1:latest — 24B parameters, Q4_K_M (4-bit) quantization, ~32k context, running locally via Ollama on hactar.unige.ch.

Design rule for all proposed changes: **simple, direct, concrete instructions work best**. "Do not X" and "Never X" are more reliable than abstract principles or complex conditionals. Fewer, shorter rules outperform long lists.

### Multi-step reply chain (`src/reply_chain.py`)

Reply drafts are generated through a **4-step chain**, NOT a single LLM call. Each step sees only its own data — no information leakage between steps.

```
INCOMING EMAIL
     │
     ▼
┌─────────────────────────────────────────────────┐
│ STEP 0: Pre-classification (rules + LLM)        │
│ Input: subject + first 200 chars of body        │
│ Output: category (INFO_REQUEST, SCHEDULE_CHANGE, │
│         COMPLAINT, INTERVENTION_Q, ADMIN, OOO,  │
│         THANKS, SIGNOUT, UNKNOWN)                │
│ OOO → no draft; THANKS → short ack; SIGNOUT → no│
│ draft                                            │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ STEP 1: Question Extraction                     │
│ Input: current email only (quoted history        │
│        stripped by strip_quoted_history())       │
│ Output: numbered list of questions the sender    │
│         asked, or fallback to first 300 chars   │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ STEP 2: Information Retrieval (3 agents)        │
│                                                  │
│ Agent A — Qualtrics Agent                        │
│   Input: questions + participant data (Q&A fmt)  │
│   Strict: "NOT FOUND" if not in data             │
│                                                  │
│ Agent B — Context Files Agent                    │
│   Input: questions + pack text (Q&A fmt)         │
│   Strict: "NOT FOUND" if not in files            │
│                                                  │
│ Agent C — Email History Agent                    │
│   Input: questions + prior correspondence        │
│   Strict: "NOT FOUND" if not discussed           │
│                                                  │
│ Which agents run depends on category recipe:     │
│ INFO_REQUEST → A:full, B:summary, C:skip         │
│ SCHEDULE_CHANGE → A:full, B:skip, C:1 email      │
│ COMPLAINT → A:full, B:skip, C:2 emails           │
│ INTERVENTION_Q → A:summary, B:full, C:skip       │
│ ADMIN → A:full, B:skip, C:skip                   │
│ UNKNOWN → A:full, B:summary, C:1 email           │
└─────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────┐
│ STEP 3: Email Writer                            │
│ Input:                                          │
│   - Current email ONLY (no history)             │
│   - Merged Q&A answers from Step 2              │
│   - Category from Step 0                        │
│   - Pending actions summary                     │
│ Output: HTML email body                         │
│                                                  │
│ Writer NEVER sees raw files or full history.     │
│ It works exclusively from Q&A answers.           │
└─────────────────────────────────────────────────┘
```

**Fallback:** If the chain fails or returns None, the old single-step approach (`build_reply_messages()` → `run_model_with_validation()`) is used as a fallback. Fallback-generated drafts may show the old class of problems (context overload, answering old questions, etc.).

### Chain prompt locations

| Component | File | Function |
|---|---|---|
| Rule-based classifier (OOO/THANKS/SIGNOUT) | `src/reply_chain.py` | `classify_rule_based()` |
| LLM classifier prompt | `src/reply_chain.py` | `build_classify_messages()` |
| Category → agent recipe | `src/reply_chain.py` | `_CONTEXT_RECIPES` dict |
| Question extraction prompt | `src/reply_chain.py` | `build_question_extraction_messages()` |
| Agent A (Qualtrics) prompt | `src/reply_chain.py` | `build_qualtrics_agent_messages()` |
| Agent B (Files) prompt | `src/reply_chain.py` | `build_files_agent_messages()` |
| Agent C (History) prompt | `src/reply_chain.py` | `build_history_agent_messages()` |
| Writer prompt | `src/reply_chain.py` | `build_writer_messages()` |
| Answer merger | `src/reply_chain.py` | `merge_agent_answers()` |
| Qualtrics Q&A formatter | `src/reply_chain.py` | `format_qualtrics_as_qa()` |
| Intervention Q&A formatter | `src/reply_chain.py` | `format_intervention_as_qa()` |
| Pending actions builder | `src/reply_chain.py` | `build_pending_actions()` |
| Quoted-history stripper | `src/reply_chain.py` | `strip_quoted_history()` |
| Chain orchestrator | `src/reply_chain.py` | `run_reply_chain()` |
| Wiring into process_message | `src/main.py` | `process_message()` (~line 2106) |

### Source files (context packs — still edit these, not the compiled JSON)

| Path | Purpose |
|---|---|
| `context/prompt/base_system_prompt.txt` | Global system message — used by the fallback single-step path and initial outreach. The chain writer (Step 3) has its own prompt in `reply_chain.py`. |
| `context/references/participants/` | Participant-specific reference material → compiled into packs → fed to Agent B |
| `context/references/facility/` | Facility reference material → compiled into packs → fed to Agent B |
| `context/references/facilitator/` | Facilitator reference material → compiled into packs → fed to Agent B |
| `context/references/all/` | Shared across all roles |

### Build-time classification pipeline (`context/build_context_packs.py`)

Source files are parsed into atomic sentences and automatically classified:

| Classifier keyword | Compiled section |
|---|---|
| "do not" / "never" / "avoid" | `must_not_say` |
| "include" / "must" / "invite" / "ask" | `must_include` |
| "pre" / "post" / weeks / months | `timeline` |
| URLs | `links` |
| everything else | `facts` |

**Consequence:** Sentences starting with "Do not…" or "Never…" added to ANY source file automatically flow into the `must_not_say` section visible to the LLM. This is the most reliable fix mechanism for a small quantized model.

### CRITICAL: Classifier routing traps

The sentence classifier splits multi-sentence text and routes each fragment independently. Common traps:

| Trigger word in sentence | Routes to | Problem |
|---|---|---|
| "please", "include", "ask", "must", "invite" | `must_include` | Compile cap 14, **render cap 8** — often full |
| "pre", "post", "before", "after", weeks/months | `timeline` | Compile cap 10, **render cap 6** — often full |
| "A:" at sentence start | `formatting` | May work (render cap 6, usually has room) |
| URL in sentence | `links` | Extracted separately; sentence body classified on its own |

**Best strategy for new facts that must be visible:**
1. **First choice:** Phrase as "Do not X" → routes to `must_not_say` (compile 14, render 12, usually has room)
2. **Second choice:** Single declarative sentence without trigger words → routes to `facts` (compile 20, render 6 — crowded)
3. **Avoid:** Multi-sentence answers, sentences with "please/include/ask", sentences with "pre/post"

**Example of rerouting a fact to must_not_say:**
- BAD: "The questionnaire should be completed as soon as possible" → `facts` (position 21+, dropped by compile cap)
- GOOD: "Do not tell participants to fill out the questionnaire 'just before the course starts' — it should be completed as soon as possible" → `must_not_say` (position 6-7, within render cap)

### CRITICAL: Double-cap truncation (context packs for Agent B)

Context packs are rendered via `render_pack_for_prompt()` before being converted to Q&A format by `format_intervention_as_qa()`. The render caps still apply:

| Section | Compile cap (`build_context_packs.py`) | **Render cap — what Agent B sees** (`compiled_context.py`) |
|---------|---------------------------------------|-------------------------------------------------------------------|
| must_include | 14 | **8** |
| must_not_say | 14 | **12** |
| timeline | 10 | **6** |
| call_to_action | 10 | **6** |
| tone | 8 | **4** |
| formatting | 10 | **6** |
| facts | 20 | **6** |
| links | 12 | **6** |

**The render cap is what matters.** If you add a 7th `must_not_say` rule, Agent B will never see it. Always verify your new rule appears in the rendered output (check the compiled pack AND count its position).

**Item ordering = priority.** Rules at the top of a source file survive truncation; rules at the bottom get dropped first. After adding a new rule, place it at the **top** of the file if it's critical, or reorder existing rules to push less important ones down.

### Runtime context flow (what each chain step sees)

**Step 0 (classifier):** Subject + first 200 chars of body. Tiny context — ~300 tokens.

**Step 1 (question extraction):** Current email body only (quoted history stripped). No Qualtrics data, no files, no thread.

**Step 2 agents — each agent sees ONLY its own data:**
- **Agent A (Qualtrics):** Extracted questions + participant data formatted as Q&A pairs by `format_qualtrics_as_qa()`. Fields include: name, gender, language, enrollment status, course details (date/time/address/canton/all dates), pipeline status (pre/post questionnaires, reminders), notes, wishes.
- **Agent B (Files):** Extracted questions + intervention/role pack text converted to Q&A by `format_intervention_as_qa()` + bucket context digest. The amount shown depends on category recipe ("full" or "summary").
- **Agent C (History):** Extracted questions + prior correspondence (1-2 emails, depending on category recipe). Skipped entirely for most categories.

**Step 3 (writer):** Current email body (no history) + merged Q&A answers from Step 2 + category + pending actions summary from `build_pending_actions()`. **Never sees raw Qualtrics data, raw files, or email thread.**

Role is resolved from the draft's Outlook folder path:
- path contains `participant` → `reply_participant` pack → `references/participants/` files
- path contains `passive` → `reply_passive_control`
- path contains `facilitator` → `reply_facilitator`
- path contains `facility` → `reply_facility`

### What to edit for each type of problem

#### Chain step fixes (identify which step is producing the error)

| Problem type | Failing step | Fix location | How |
|---|---|---|---|
| Wrong category (wrong agents activated) | Step 0 | `reply_chain.py` → `classify_rule_based()` or `build_classify_messages()` | Add keyword to rule-based classifier, or refine LLM prompt |
| Missed question / wrong question extracted | Step 1 | `reply_chain.py` → `build_question_extraction_messages()` | Refine extraction prompt |
| Agent A says NOT FOUND but data exists | Step 2A | `reply_chain.py` → `format_qualtrics_as_qa()` | Add missing Q&A pair for the field |
| Agent B says NOT FOUND but info is in reference files | Step 2B | Reference file in `context/references/{role}/` or `reply_chain.py` → `format_intervention_as_qa()` | Add fact to reference file (→ rebuilds pack) or fix Q&A conversion |
| Agent C misreads email history | Step 2C | `reply_chain.py` → `build_history_agent_messages()` | Refine history agent prompt |
| Wrong agent skipped for this category | Step 2 | `reply_chain.py` → `_CONTEXT_RECIPES` | Adjust recipe: change "skip" to "full"/"summary", increase `history_depth` |
| Writer includes forbidden info | Step 3 | `reply_chain.py` → `build_writer_messages()` | Add rule to writer system prompt |
| Writer uses wrong tone/salutation | Step 3 | `reply_chain.py` → `build_writer_messages()` | Add tone instruction to writer prompt |
| Writer hallucinates (answers beyond Q&A) | Step 3 | `reply_chain.py` → `build_writer_messages()` | Strengthen "only use provided Q&A" rule |
| Quoted history leaks into current email | Pre-Step 1 | `reply_chain.py` → `strip_quoted_history()` → `_QUOTE_MARKERS` | Add new regex pattern for the quote marker format |

#### Contextual fixes (content changes to source/reference files)

| Problem type | Best fix location | Why |
|---|---|---|
| LLM mentions forbidden info | Add "Do not X" to the role's reference file | → auto-classified to `must_not_say` → fed to Agent B |
| LLM uses wrong salutation / first name | Writer prompt in `reply_chain.py` → `build_writer_messages()` has salutation rules. If still wrong, add to reference file as "Do not X". | |
| LLM hallucinates a fact | Add the correct fact to the reference file | → goes into `facts` section → visible to Agent B |
| Problem affects ALL roles | Edit writer prompt in `reply_chain.py` → `build_writer_messages()` system prompt | Global for chain path |
| Problem is role-specific | Edit the role's `context/references/<role>/` file | Role-specific `must_not_say`/`facts` |
| LLM reveals programme/control-group info | Verify `forbidden_terms` covers it; add "Do not X" rule; add to writer prompt | Hard principle: participants never learn about SH+/COG/POD/passive control |
| Missing participant field in Agent A output | `reply_chain.py` → `_format_participant_qa()` | Add new Q&A pair for the Qualtrics column |
| Pending action status wrong/missing | `reply_chain.py` → `build_pending_actions()` → `_DRAFT_COLUMNS` | Add/fix column mapping |

**Never add complex conditionals.** If you need "only mention X if…", prefer "Do not mention X" with a separate fact entry for when it IS appropriate.

#### Structural fixes (pipeline changes — use when contextual fixes are insufficient)

| Problem type | Fix location | Example |
|---|---|---|
| Critical rule dropped by render cap | **Reorder items** in source file — move to top | Move cost rule to line 1 of `participants_info.txt` |
| Section consistently too small | **Raise render cap** in `src/compiled_context.py` (line ~183) | Increase `must_not_say` from 6 → 8 |
| Word/phrase must never appear regardless of rules | **Add to `forbidden_terms`** in pack validation (`build_context_packs.py` PackSpec) | Add "rendez-vous" to forbidden_terms |
| Word/phrase must always appear | **Add to `required_terms`** in pack validation | Add "questionnaire" to required_terms |
| Agent A needs participant data it's not getting | **Add field** to `format_qualtrics_as_qa()` in `src/reply_chain.py` | Add intervention-code Q&A pair |
| Category misroutes consistently | **Adjust `_CONTEXT_RECIPES`** in `src/reply_chain.py` | Change ADMIN recipe to include Agent B |
| Chain fails and fallback triggers | **Debug `run_reply_chain()`** — check logs for which step errored | Fix the underlying step, or improve fallback path |
| Same error keeps recurring (3+ times in feedback log) | **Systemic fix** — rethink the approach | Maybe the rule is too subtle for Mistral; move logic to validation instead |
| Fact must NOT go to `facts` section (needs higher priority) | **Rephrase as "Do not X"** to route it to `must_not_say` instead | "Do not say participation has a cost" instead of "Participation is free" |

**When to choose structural over contextual:** If a contextual fix was already tried for the same class of problem (check `feedback_log.jsonl`) and the error recurred, escalate to a structural fix.

To see what is currently compiled for a pack:
```bash
cat context/compiled/context_packs.json | python3 -c "
import json,sys
data = json.load(sys.stdin)
pack = next(p for p in data['packs'] if p['pack_id'] == 'reply_participant')
print(json.dumps(pack['sections'], indent=2))
"
```

---

## Knowledge sources for self-diagnosis

When a draft has no red/yellow annotations, load these sources in priority order to diagnose independently:

1. **The original incoming email** — what the sender actually asked
   → Fetch via `conversationId` from the draft (use Graph API snippet in the reference section below)
2. **The chain logs** — which step ran, what category was assigned, how many questions extracted
   → Check server logs: `journalctl ... | grep 'chain step\|reply chain'`
3. **The chain prompts** — what each step was told to do
   → `src/reply_chain.py` — the system prompts in `build_*_messages()` functions
4. **The Q&A format for this sender** — what Agent A actually received
   → Run `format_qualtrics_as_qa()` on the sender's Qualtrics rows
5. **The compiled context pack** for the draft's role — what Agent B received
   → `context/compiled/context_packs.json` — filter to `pack_id` matching the role
6. **The feedback log** — known recurring error patterns
   → `context/feedback_log.jsonl`
7. **The role's reference files** — factual ground truth
   → `context/references/{role}/` (all `.txt` files)
8. **The fallback prompt template** — used when the chain fails
   → `context/prompt/reply_user_prompt.txt` + `base_system_prompt.txt`

**Future:** A synthesised "ADVANCE project knowledge base" document may be created from all reference files, Melanie Mack's shared project files (`Fichiers de Melanie Mack - ADVANCE/`), and the email draft manual. This would give a single comprehensive reference for fact-checking. Until then, read the individual files above.

### Fetching the original incoming email

```python
# From email_draft_automation/ with .env loaded
import sys; sys.path.insert(0, 'src')
from graph_mail import build_graph_service_from_env
mail = build_graph_service_from_env()

# Use the draft's conversationId to find the original inbound message
conv_id = "CONVERSATION_ID_FROM_DRAFT"
safe = conv_id.replace("'", "''")
resp = mail._request("GET", f"/users/{mail.mailbox}/messages", params={
    "$filter": f"conversationId eq '{safe}' and isDraft eq false",
    "$select": "id,subject,from,body,bodyPreview,receivedDateTime",
    "$top": 10,
    "$orderby": "receivedDateTime desc",
})
for m in resp.json().get("value", []):
    sender = m.get("from", {}).get("emailAddress", {}).get("address", "")
    if "advance-project" not in sender.lower():
        print(f"Original from {sender}: {m['subject']}")
        print(m.get("bodyPreview", "")[:500])
        break
```

---

## Step 3 — Diagnose root cause

### First: Identify which chain step produced the error

Before diving into content analysis, determine **which step in the chain** is responsible. This narrows the search dramatically.

**Quick chain-step triage:**

| Symptom | Likely step | Investigation |
|---|---|---|
| Draft answers a question nobody asked | Step 1 (extraction) — extracted a phantom question | Check what questions were extracted |
| Draft answers a question from a *previous* email, not the current one | Step 1 or pre-Step 1 — `strip_quoted_history()` failed to strip quotes | Check if quoted text leaked into the current body |
| Draft has correct answers but wrong ones are NOT FOUND | Step 2 — one agent couldn't find the data | Check Agent A/B/C outputs; is the data in the Q&A format? |
| Draft mentions info it shouldn't have access to | Step 2 — wrong agent recipe for this category | Check category from Step 0; was the right recipe used? |
| Draft tone is wrong / wrong salutation / wrong language | Step 3 (writer) — writer prompt issue | The writer prompt controls tone and format |
| Draft hallucinates facts not in any source | Step 3 (writer) — writer went beyond Q&A answers | The "only use provided Q&A" constraint needs strengthening |
| No draft created for a legitimate email | Step 0 — misclassified as OOO/SIGNOUT | Check if rule-based classifier matched a false positive |
| Draft is generic/vague despite data being available | Step 2 — agents returned NOT FOUND, or answers were lost in merge | Check each agent's output and the merged Q&A |
| Draft looks like old-style (all context dumped) | Chain failed → fallback triggered | Check server logs for "falling back to single-step" |

**To inspect chain execution**, check the server logs:
```bash
ssh -i ~/.ssh/ssh-key leitneruser@10.40.41.88 \
  "journalctl -u email-draft-automation-cycle.service --since '1 hour ago' --no-pager | grep -i 'chain step\|reply chain\|falling back'"
```

Key log lines to look for:
- `Chain Step 0: category = X` — what category was assigned
- `Chain Step 1: extracted N question(s)` — how many questions found
- `Chain Step 2: merged answers from N agent(s)` — which agents responded
- `Chain Step 3: generated reply body (N chars)` — writer output
- `Reply chain failed ... falling back to single-step` — chain crashed, fallback used

### Path A: Annotated drafts (red/yellow present)

For drafts with `red_parts` and/or `yellow_instructions`, reason through:

1. **What is wrong** (from `red_parts`): Is the LLM including forbidden information? Using wrong tone? Hallucinating facts? Being too long? Wrong language register?

2. **Why did it happen** — trace to the responsible chain step:
   - **Step 0 issue:** Email was misclassified → wrong agents ran → wrong/missing info. Fix: adjust `classify_rule_based()` keywords or `build_classify_messages()` prompt, or adjust `_CONTEXT_RECIPES`.
   - **Step 1 issue:** Questions weren't extracted correctly → agents answered wrong things. Fix: refine `build_question_extraction_messages()` prompt.
   - **Step 2A issue:** Qualtrics data exists but Agent A said NOT FOUND → field missing from `format_qualtrics_as_qa()`. Fix: add Q&A pair for the column.
   - **Step 2B issue:** Reference file has the info but Agent B said NOT FOUND → fact is in a section truncated by render cap, or `format_intervention_as_qa()` didn't convert it properly. Fix: reorder items in source file or add fact.
   - **Step 2C issue:** Email history wasn't consulted → `history_depth` is 0 for this category. Fix: adjust `_CONTEXT_RECIPES`.
   - **Step 3 issue:** Writer produced bad output despite having correct Q&A answers. Fix: refine `build_writer_messages()` system prompt.
   - **A rule exists but was truncated by the render cap** — check the item's position in the compiled pack
   - **A recurring pattern** already seen in `feedback_log.jsonl` — needs a structural fix, not another rule

3. **What to fix** (from `yellow_instructions`): Use the reviewer's instructions as the signal for what the rule should say.

### Path B: Unannotated drafts (no red/yellow — self-diagnosis)

When `red_parts` and `yellow_instructions` are both empty, follow this checklist systematically:

**B1. Fetch the original incoming email** using the conversationId (see snippet above). Read what the sender actually asked.

**B2. Check chain step logs** (if accessible) — see which category was assigned, what questions were extracted, and whether agents returned NOT FOUND.

**B3. Check must_not_say violations** — load the compiled context pack for the draft's role and compare each `must_not_say` rule against the draft body:
- Does the draft mention programme duration, session count, or schedule without being asked?
- Does it reveal exact venue/address before pre-questionnaire completion?
- Does it provide compensation details, questionnaire links, or course descriptions unsolicited?
- Does it offer to check/modify/reschedule courses instead of directing to Qualtrics re-registration?
- Does it mention other intervention programmes or compare them?
- Does it reveal anything about programme allocation, control groups, or intervention types (SH+, COG, POD)?
  **Hard principle:** Participants must NEVER learn about the difference between workshops, the existence of a passive control group, or how allocation works. If asked about their programme assignment, the only answer is: "You will be informed after completing the pre-assessment questionnaire."

**B4. Check must_include compliance** — for the topic the sender asked about, are the required facts present?
- If asked about signing up → questionnaire link should be included
- If asked about dates/times → direct to Qualtrics landing page (not provide specific dates)
- If asked about cost → "free" + "CHF 100 at end" (not broken down per questionnaire)

**B5. Check for hallucinations** — compare any specific claims in the draft (dates, times, locations, names, URLs) against:
- The compiled context pack's `links` and `facts` sections
- The role's reference files in `context/references/{role}/`
- The Qualtrics Q&A that Agent A would have received — run `format_qualtrics_as_qa()` on the sender's row to see
- If the draft states something not found in any source → hallucination

**B6. Check tone and language**:
- Correct language? (FR/DE matching the incoming email)
- Formal salutation with family name only? (not first name, not "Cher/Chère")
- Answers only what was asked? (no info-dumping — the most common Pattern C error)
- No closing signature block? (branding is automatic)

**B7. Cross-reference with feedback log** — read `context/feedback_log.jsonl` and check if any known patterns match:
- Pattern A: offering to check/modify courses instead of re-registration
- Pattern B: sharing link without mentioning landing page availabilities
- Pattern C: info-dumping unsolicited details
- Pattern D: revealing address before pre-questionnaire
- Pattern E: using first name instead of family name in salutation (systemic — 4/8 in batch #5)
- Pattern F: reducing recurring weekday constraint ("every Monday") to single date
- Pattern G: misunderstanding questionnaire link (claiming link is only descriptive)
- Pattern H: hallucinating questionnaire timing ("just before the course starts")
- Pattern I: wrong category → wrong context recipe → missing info (chain-specific)
- Pattern J: question not extracted → implicit fallback used → vague answer (chain-specific)
- Pattern K: Agent A returns NOT FOUND when field exists in Q&A format (chain-specific)
- Pattern L: quoted history leaked into current email → answered old questions (chain-specific)

**B8. If still unclear** — ask the user: "I reviewed this draft against the context pack rules and reference files but couldn't identify a clear violation. Could you point out which part is imperfect, or describe what feels wrong?"

4. **Cross-pack impact check**: Changes to shared files affect multiple packs. Before applying:
   - `references/participants/*.txt` → affects both `reply_participant` AND `initial_participant`
   - `references/all/*.txt` → affects ALL packs
   - Chain prompts in `reply_chain.py` → affect ALL chain-generated reply drafts (all roles)
   - `base_system_prompt.txt` → affects fallback path + initial outreach

   After applying a fix, verify it doesn't break other packs by checking the compiled sections for all affected pack IDs.

---

## Step 4 — Propose a minimal, targeted change

Propose the **smallest possible edit** that fixes this class of problem for all future drafts.

### Chain-step fixes (edit `src/reply_chain.py`):
- **Step 0:** Add keyword to `_OOO_KEYWORDS`/`_SIGNOUT_KEYWORDS`/`_THANKS_KEYWORDS`, or refine `build_classify_messages()` prompt, or adjust `_CONTEXT_RECIPES` dict
- **Step 1:** Refine `build_question_extraction_messages()` system prompt
- **Step 2A:** Add Q&A pair to `_format_participant_qa()` for a missing Qualtrics field
- **Step 2B:** Refine `build_files_agent_messages()` prompt, or fix `format_intervention_as_qa()` parsing
- **Step 2C:** Refine `build_history_agent_messages()` prompt, or change `history_depth` in recipe
- **Step 3:** Add rule to `build_writer_messages()` system prompt (salutation, tone, forbidden info)
- **Merge:** Fix `merge_agent_answers()` if answers are being lost or misordered
- **Quote stripping:** Add regex to `_QUOTE_MARKERS` list if a new quote format isn't being caught

### Context-pack fixes (edit reference files):
- Add one bullet to a `must_not_say` section in a reference file
- Correct a factual sentence in a reference file

### Fallback-path fixes (edit prompt files):
- Add one line to `base_system_prompt.txt` (affects fallback + initial outreach)

**Always show the exact diff** before applying:
```
File: src/reply_chain.py
Function: build_writer_messages()
Add to system_prompt: "- Never mention the number of training sessions or session schedule unless directly asked"
```

Wait for user approval before applying any change.

---

## Step 5 — Apply approved changes

Edit the source file directly. Keep changes minimal — add a bullet, fix a sentence. Never rewrite whole sections.

### If the fix is in a reference file (context pack content):

**If the fix is a new rule:** Place it at the **top** of the source file if it's critical. Items are truncated from the bottom — position = priority.

After applying, rebuild the context packs:
```bash
cd email_draft_automation
./run/run_build_context_packs.sh
```

Confirm the change appears in the compiled pack:
```bash
cat context/compiled/context_packs.json | python3 -c "
import json,sys
packs = json.load(sys.stdin)
pack = next(p for p in packs if p['pack_id'] == 'PACK_ID')
print(json.dumps(pack['sections'], indent=2))
"
```

**Verify it survives the render cap.** Use this one-liner to check all new items at once:

```bash
cd email_draft_automation
./run/run_build_context_packs.sh && python3 -c "
import json
data = json.load(open('context/compiled/context_packs.json'))
caps = {'facts': 6, 'must_include': 8, 'must_not_say': 12, 'timeline': 6, 'call_to_action': 6, 'formatting': 6, 'links': 6, 'tone': 4}
SEARCH = ['keyword1', 'keyword2']  # ← replace with keywords from your new rules
for p in data['packs']:
    for section, items in p['sections'].items():
        for i, item in enumerate(items, 1):
            if any(kw in item.lower() for kw in SEARCH):
                cap = caps.get(section, 99)
                status = 'VISIBLE' if i <= cap else 'TRUNCATED'
                print(f'[{p[\"pack_id\"]}/{section} #{i}/{len(items)} — {status}] {item[:120]}')
"
```

If an item shows `TRUNCATED`, fix it:
1. Reorder items in the source file to push this rule higher, OR
2. Raise the render cap in `src/compiled_context.py` (the `limit` values around line 183), OR
3. **Rephrase to route to a less-crowded section** — this is usually the fastest fix:
   - Rephrase a fact as "Do not X" to route from `facts` → `must_not_say`
   - Remove "please/include/ask" to avoid `must_include`
   - Remove "pre/post/before/after" to avoid `timeline`
   - See the classifier routing traps table in Step 2

### If the fix is in chain prompts (`src/reply_chain.py`):

No context pack rebuild needed — chain prompts are read directly from Python code. Changes take effect on the next automation cycle.

**Verify with a quick syntax check:**
```bash
cd email_draft_automation
python3 -c "import ast; ast.parse(open('src/reply_chain.py').read()); print('OK')"
```

**For Q&A format changes** (new field in `format_qualtrics_as_qa()` or `format_intervention_as_qa()`), verify with a smoke test:
```python
cd email_draft_automation
python3 -c "
from src.reply_chain import format_qualtrics_as_qa
# Test with a sample row containing the new field
row = {'sheet': 'part', 'part_first': 'Test', 'part_last': 'User', 'NEW_FIELD': 'value'}
print(format_qualtrics_as_qa([row]))
"
```

**For classification changes** (keywords or recipe), verify:
```python
cd email_draft_automation
python3 -c "
from src.reply_chain import classify_rule_based, get_context_recipe, EmailCategory
# Test that the new keyword triggers the expected category
result = classify_rule_based('Subject', 'Body with new keyword')
print(f'Classified as: {result}')
if result: print(f'Recipe: {get_context_recipe(result)}')
"
```

### Deploy after changes

For **all fix types** (reference files AND chain code), commit and deploy:
```bash
cd email_draft_automation && git add -A && git commit -m 'refine-drafts: <brief description>'
# Then push → pull on server (see CLAUDE.md deploy instructions)
```

---

## Step 6 — Re-queue or clean up the draft

**Check the `source` field** of each draft to decide what to do:

### Category-tagged drafts (`source: "category"`) — re-queue

These are the original drafts that haven't been sent. Delete the draft and mark the original message unread so the reply agent re-generates it on the next cycle:

```bash
cd email_draft_automation
set -a && source .env && set +a
.venv/bin/python3 src/replace_draft.py --id DRAFT_ID
```

Use `--dry-run` first to verify the right message will be affected.

**WARNING: `replace_draft.py` requires the draft to still exist.** If you already deleted the draft (e.g. via `mail.delete_message()`), `replace_draft.py` will 404 and the original message will NOT be marked unread. In that case, find the original message manually and mark it unread:

```python
# Find original by searching for the sender's reply
resp = mail._request("GET", f"/users/{mail.mailbox}/messages", params={
    "$search": '"from:SENDER_EMAIL subject:SUBJECT_FRAGMENT"',
    "$select": "id,subject,from,isRead,isDraft",
    "$top": 5,
}, headers={"ConsistencyLevel": "eventual"})
for m in resp.json().get("value", []):
    if not m.get("isDraft") and m.get("isRead"):
        mail.mark_message_unread(m["id"])
        print(f"Marked unread: {m['subject'][:50]}")
```

**Best practice:** Always run `replace_draft.py` BEFORE deleting drafts manually. If batch-processing, call it once per draft — do not delete first then try to re-queue.

### Imperfect-folder drafts (`source: "folder"`) — delete only, do NOT re-queue

These are **copies** that the reviewer placed in the imperfect folder for improvement purposes. The original draft was already edited and sent manually. Re-queuing would create a duplicate reply.

Just delete the copy:

```python
mail.delete_message("DRAFT_ID")
```

Do **not** call `replace_draft.py` and do **not** mark the original message as unread.

---

## Step 7 — Log the feedback

Append an entry to `context/feedback_log.jsonl`:

```python
import json, datetime, pathlib

entry = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "draft_id": "...",
    "role": "participant",
    "language": "DE",
    "red_parts": ["..."],
    "yellow_instructions": ["..."],
    "diagnosis": "...",
    "chain_step": "step_3_writer",  # step_0_classify | step_1_extract | step_2a_qualtrics | step_2b_files | step_2c_history | step_3_writer | fallback
    "chain_category": "INFO_REQUEST",  # category assigned by Step 0, or "fallback" if chain failed
    "file_changed": "src/reply_chain.py",  # or "context/references/..."
    "change_summary": "Added: '...'",
    "draft_requeued": True,
}
pathlib.Path("context/feedback_log.jsonl").open("a").write(json.dumps(entry, ensure_ascii=False) + "\n")
```

---

## Graph API Quick Reference

All snippets run from `email_draft_automation/` with the `.env` loaded:

```bash
cd email_draft_automation
set -a && source .env && set +a
```

### Setup

```python
import sys; sys.path.insert(0, 'src')
from graph_mail import build_graph_service_from_env
mail = build_graph_service_from_env()
```

### List drafts tagged "Imperfect"

```python
resp = mail._request("GET", f"/users/{mail.mailbox}/messages", params={
    "$filter": "isDraft eq true and categories/any(c:c eq 'Imperfect')",
    "$select": "id,subject,conversationId,parentFolderId",
    "$top": 50,
})
for m in resp.json().get("value", []):
    print(m["id"], m["subject"])
```

### Fetch a specific message by ID

```python
msg = mail.fetch_message("MESSAGE_ID")
print(msg.subject, msg.body)        # GraphMessage attrs
print(msg.conversation_id)
```

### Find original incoming email by conversation ID

```python
PROJECT_MAILBOX = "advance-project@unige.ch"
conv_id = "CONVERSATION_ID"
safe = conv_id.replace("'", "''")
resp = mail._request("GET", f"/users/{mail.mailbox}/messages", params={
    "$filter": f"conversationId eq '{safe}' and isDraft eq false",
    "$select": "id,subject,from,isRead",
    "$top": 20,
})
for m in resp.json().get("value", []):
    sender = m.get("from", {}).get("emailAddress", {}).get("address", "")
    if PROJECT_MAILBOX.lower() not in sender.lower():
        print("Original:", m["subject"], m["id"])
```

### Delete a draft/message

```python
mail.delete_message("MESSAGE_ID")   # moves to Deleted Items
```

### Mark a message as unread

```python
mail.mark_message_unread("MESSAGE_ID")
```

### List messages in a folder

```python
# well-known names: "drafts", "inbox", "sentitems", "deleteditems"
resp = mail._request("GET", f"/users/{mail.mailbox}/mailFolders/drafts/messages", params={
    "$select": "id,subject,isDraft,parentFolderId",
    "$top": 25,
})
for m in resp.json().get("value", []):
    print(m["id"], m["subject"])
```

### Delete draft + mark original unread (combined)

This is what `src/replace_draft.py` does — use the script for the normal workflow:

```bash
.venv/bin/python3 src/replace_draft.py --dry-run --id DRAFT_ID
.venv/bin/python3 src/replace_draft.py --id DRAFT_ID
```

Or manually when the draft is already gone but the original still needs re-queuing:

```python
# (after Setup above)
mail.mark_message_unread("ORIGINAL_MESSAGE_ID")
```

---

## Important constraints

- **Never write a draft email yourself.** Only improve the context/prompt infrastructure.
- **Minimal changes only.** One targeted fix per problem. Don't refactor or rewrite whole files.
- **Always show the diff before applying** and wait for user approval.
- **Rebuild context packs** (`./run/run_build_context_packs.sh`) after every reference file change. NOT needed for chain prompt changes in `reply_chain.py`.
- **`context/compiled/context_packs.json` is generated** — never edit it directly.
- The feedback log (`context/feedback_log.jsonl`) accumulates over time — never truncate it.
- **Chain prompts live in `src/reply_chain.py`** — this is now the primary file for reply-draft behaviour. Changes here affect all chain-generated replies across all roles.
- **The fallback path still uses the old single-step approach** — `base_system_prompt.txt` and `reply_user_prompt.txt` still matter for when the chain fails. Keep both paths working.
