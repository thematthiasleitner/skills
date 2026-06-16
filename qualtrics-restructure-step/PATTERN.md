# Patterns extracted from the 7 reference restructure scripts

Read this BEFORE writing a new restructure script. It distils the design rules
that emerged from Phase 4 iterations 1, 2, 5a, 5b, 5c, 6, 7 of
`docs/facility_address_first_plan.md`.

The reference scripts live in `email_draft_automation/tools/`:
- `restructure_facility_step_1_add_kind.py` (280 lines, ADD_QUESTION)
- `restructure_facility_step_2_rename_tags.py` (203 lines, RENAME_TAG, batch)
- `restructure_facility_step_5a_add_slots.py` (299 lines, ADD_QUESTION, batch + block reorder)
- `restructure_facility_step_5b_remove_legacy_slots.py` (166 lines, BLOCK_REORDER)
- `restructure_facility_step_5c_slot_count_gating.py` (208 lines, DISPLAY_LOGIC, batch)
- `restructure_facility_step_6_zoom_display_logic.py` (239 lines, DISPLAY_LOGIC, batch)
- `restructure_facility_step_7_tighten_slot_force.py` (188 lines, VALIDATION_CHANGE, batch)

---

## Rule 1: One logical change per script

A single restructure script does ONE thing. Multiple loosely-related changes
get separate scripts that can be applied (and rolled back) independently.

If the user asks for "rename 3 tags AND add display logic to 12 questions",
push back: that's 2 iterations. Smaller iterations = smaller blast radius.

## Rule 2: --dry-run by default, --apply opt-in

```python
p.add_argument("--apply", action="store_true",
               help="Make real API calls. Default is dry-run (read-only).")
```

The script must run safely with no flags and print exactly what it WOULD do.
Running with `--apply` only after the user reviews the dry-run output.

## Rule 3: Idempotency probe before any mutation

Re-running the script (or running it after a partial failure) must skip
already-applied changes. The probe depends on mutation type:

| Mutation | Idempotency probe |
|---|---|
| ADD_QUESTION | Search `Questions` for any with `DataExportTag == new_tag` |
| RENAME_TAG | Search for the NEW tag (rename already happened if present) |
| DISPLAY_LOGIC | `gate_qid in json.dumps(question["DisplayLogic"])` |
| VALIDATION_CHANGE | `settings.get("ForceResponse") == "ON"` etc. |
| BLOCK_REORDER | Target QID absent from `block["BlockElements"]` |

Skip the operation, print `[skip] reason`, and continue. Don't error.

## Rule 4: Plan → print → apply, with per-op tracking

```python
# Planning phase (always runs, regardless of --apply)
to_update = []
for ...:
    if not already_done(...):
        to_update.append((qid, tag, payload))
        print(f"  [plan] {qid} ({tag}) — ...")

# Dry-run early exit
if not args.apply:
    print(f"  would PUT {len(to_update)} questions")
    return 0

# Apply with per-op failure tracking
failures = []
for qid, tag, payload in to_update:
    r = put_question(...)
    if not r.ok:
        failures.append((qid, tag, f"{r.status_code} {r.text[:200]}"))
    else:
        print(f"  done {qid}")

# Final summary
print(f"  updated: {len(to_update) - len(failures)}")
print(f"  failed : {len(failures)}")
return 1 if failures else 0
```

A partial-success run (e.g. 8/12 PUTs succeed) reports honestly. Re-running
finishes the remaining 4 via the idempotency probe.

## Rule 5: Use the canonical payload-builders, never invent shapes

Qualtrics is picky about question and DisplayLogic JSON shapes. Always
pattern-match from existing live questions (use `GET /survey-definitions/{id}/questions/{qid}`
on a similar question) rather than guess. Wrong shapes get rejected with
opaque `400 Bad Request`.

Known canonical shapes:
- **MC with 2 choices + RecodeValues**: see `step_1_add_kind.py` (mirrors `f_ty_room_table`)
- **TE single line for date / time**: see `step_5a_add_slots.py` (mirrors `f_ty_room_N_t1_begin`)
- **MC single-choice "I confirm"**: see `step_5a_add_slots.py`
- **DisplayLogic "show if X==Y"** (per-loop-iteration): see `step_6_zoom_display_logic.py`
- **DisplayLogic "show if X in {a,b,c,d}"** (OR chain): see `step_5c_slot_count_gating.py`
- **DisplayLogic "show if A AND (B OR C OR D)"** (two groups): see
  `step_9_zoom_url_slot_gate.py`

### Two-group AND DisplayLogic ("A AND (B OR C…)")

There may be **no live two-group example in the survey to copy** (there wasn't,
2026-06-12 — every existing DisplayLogic was a single group). The canonical
Qualtrics shape, confirmed by PUT→GET round-trip:

```python
{
  "0": {"0": exprA,                    # group 0: first expr has NO Conjuction key
        "Type": "If"},
  "1": {"0": {**exprB, "Conjuction": "And"},   # inter-group AND lives on the
        "1": {**exprC, "Conjuction": "Or"},    #   FIRST expr of the SECOND group
        "2": {**exprD, "Conjuction": "Or"},
        "Type": "If"},
  "Type": "BooleanExpression", "inPage": False,
}
```

Rules: top-level numbered groups `"0"`,`"1"`,…; the **inter-group conjunction is
carried as `"Conjuction":"And"` on the first expression of each subsequent
group** (Qualtrics' misspelling); within a group, expr `i>0` carry
`"Conjuction":"Or"`; group-0 expr-0 carries none. Preserve the *existing* group
verbatim and **append** the new group (don't rebuild group 0). Loop-block targets
still need `QuestionIsInLoop:"yes"` + `LoopAndMergeLoops:"current"` on every expr
(Rule 7). Since there's no live template, **apply to ONE question first, GET it
back to confirm Qualtrics accepted+preserved the shape, then batch the rest**
(`step_9` has a `--only QID` flag + a post-PUT `verify_applied` GET for exactly
this).

## Rule 6: BlockElements reorders MUST preserve everything not explicitly moved

```python
# Build NEW BlockElements list explicitly. Don't try in-place mutation.
all_legacy = {qid for qids in LEGACY_SLOT_QIDS.values() for qid in qids}
new_elements = [e for e in elements if e.get("QuestionID") not in all_legacy]
block["BlockElements"] = new_elements
put_block(...)
```

Page breaks (`{"Type": "Page Break"}`), randomization elements, and any
other non-Question element types must pass through unchanged.

## Rule 7: For Loop & Merge blocks, ALL questions need loop semantics

If the target block is part of a Loop & Merge configuration (like
`f_ty_room_loop`), `DisplayLogic` entries must include:

```python
"QuestionIsInLoop": "yes",
"LoopAndMergeLoops": "current",
"LoopTarget": "none",
```

Without `"current"`, the logic evaluates against iteration 1's answer for
ALL iterations — silently wrong. Pattern-match from
`step_6_zoom_display_logic.py:build_display_logic`.

## Rule 8: Per-choice RecodeValues for canonical workbook strings

When the question text differs across languages but the workbook needs a
single canonical value (e.g. "Physical"/"Zoom" regardless of DE/FR display):

```python
payload["Choices"] = {
    "1": {"Display": "Vor Ort"},
    "2": {"Display": "Online via Zoom"},
}
payload["VariableNaming"] = {"1": "Physical", "2": "Zoom"}
payload["RecodeValues"] = {"1": "Physical", "2": "Zoom"}
payload["Language"]["FR"]["Choices"] = {
    "1": {"Display": "Sur place"},
    "2": {"Display": "En ligne via Zoom"},
}
```

Both `VariableNaming` and `RecodeValues` need the same dict (Qualtrics quirk).
CSV export with `useLabels=True` returns the recoded value, not the display.

## Rule 9: Commit message format

```
Phase {N} iter {M}: {short verb} {target}

{1-paragraph why}

Live state post-apply (verified by Layer C):
  - {count} of {what} {action}
  - survey-invariants: {N_before} → {N_after} questions
  - dispatch-tags: {N_before} → {N_after} facility tags
  - {any other Layer C count changes}

Script idempotent via {probe description}.

Plan: docs/{plan_filename}.md (Phase {N}, iter {M})
```

## Anti-patterns to avoid

- **No bulk `PUT /survey-definitions` for partial updates.** It's atomic, so
  one bad field rejects the entire change.
- **Don't delete questions** — unlink from BlockElements instead. Archived
  response data is tied to QIDs.
- **Don't rename `DataExportTag` without checking code references.** Several
  non-test scripts (`update_recruitment_validations.py`,
  `update_force_response.py`, `layer_c_smoke.py`) hard-code old tag strings.
  Renames require companion code updates.
- **Don't apply force-response to questions that don't have display-logic
  gating.** A facility declaring 1 slot would be forced to fill slots 2/3/4
  (the iter 5a→5c→7 lesson).
- **Don't trust dry-run alone for live mutations.** Always pair with the
  `/qualtrics-e2e-pressure-test` skill after `--apply`.
