---
name: glossary
description: Look up a term in the ADVANCE FR/DE/EN glossary (glossary_ADVANCE_v1.json, 218 entries). Returns canonical mappings + definition + source_ref. Tries exact → substring → all-tokens → article-stripped → fuzzy match, in that order. Pure read-only local lookup; no LLM. Invoke whenever you (or the user) need to verify the canonical translation of a domain term — e.g. checking whether 'engagement social' maps to 'soziale Einbindung', or 'être accroché' to 'am Haken sein' — without grepping the JSON by hand.
---

# glossary

Fast, deterministic lookup against the ADVANCE FR/DE/EN glossary. Replaces the 5-line inline grep+jq+python dance the maintainer used to run several times per session during translation review.

## When to invoke

- User typed `/glossary <term>`.
- User asks any variant of "what's the German for X" or "what does Y translate to" or "is Z in the glossary".
- During reviewer-audit or translation work: ANY time you're about to suggest a FR→DE substitution, verify it against the glossary first — this skill is your read path.

## Invocation

Single positional arg, a term in any of the three glossary languages:

```bash
python ~/.claude/skills/glossary/glossary_lookup.py "<term>"
```

Examples:

```bash
python ~/.claude/skills/glossary/glossary_lookup.py "engagement social"
python ~/.claude/skills/glossary/glossary_lookup.py accroché
python ~/.claude/skills/glossary/glossary_lookup.py "Innere Balance"
python ~/.claude/skills/glossary/glossary_lookup.py "Brain pampering"
```

Override the glossary file (e.g. for an experimental v2) with `--glossary PATH`.

Exit code: `0` if at least one match (including fuzzy), `1` if nothing found, `2` on I/O / parse error.

## Behavior

The helper tries match strategies in this order, stopping at the first non-empty result:

1. **Exact** (case- and diacritic-insensitive) on `src` / `tgt` / `english`.
2. **Substring** (term ≥ 3 chars) anywhere in `src` / `tgt` / `english`.
3. **All-tokens** — every whitespace-split token of the query must appear in `src` OR `tgt` OR `english`.
4. **Article-stripped retry** — drops leading `l'`, `le`, `la`, `der`, `die`, `das`, `the`, etc., and re-tries exact + substring. Catches `l'engagement social` ↔ `engagement social`.
5. **Fuzzy fallback** — top 5 candidates by `difflib.SequenceMatcher.ratio` ≥ 0.4 on any field. Output is clearly labelled as "no direct match".

Results are sorted by `source_ref` recency — entries with the newest dated `source_ref` first (e.g. `v2_reviewer_feedback_2026-05-21` outranks `COG_group sessions_manual fr_CB_final`). This matters when the same FR term has multiple DE renderings across source documents: the most-recently-reviewed entry is the canonical one.

## Output format

Plain text, one entry per match:

```
[1] FR: engagement social
    DE: soziale Einbindung
    EN: social engagement
    src_ref: v2_reviewer_feedback_2026-05-21
    def: canonical mapping (without leading article).
```

Definition truncated to ~200 chars. Output stays under ~30 lines for typical queries.

## Reading the output

- **Multiple matches** are normal — `engagement social` returns 3+ (the bare form, `l'engagement social`, and the session-title phrase). The top entry is the most recently reviewed canonical mapping; the others provide context (full sentences, capitalised variants).
- **`v2_reviewer_feedback_2026-05-21` source_ref** = post-Melanie/Theresa review, current canonical. Trust these over older source_refs in case of conflict.
- **No match + fuzzy fallback** = the term genuinely isn't in the glossary. Don't invent a translation; surface this to the user.

## Hard constraints

- **READ-ONLY.** Never modify the glossary file from this skill. If a missing term needs to be added, surface that to the user; they'll edit the glossary via `tools/build_glossary_from_docx.py` or hand-edit.
- **No LLM calls.** Pure local lookup. If the answer isn't in the JSON, say so.
- **Path-independent invocation.** The default glossary path is hardcoded as the OneDrive-synced repo path — don't require the user to `cd` first.

## File layout

```
~/.claude/skills/glossary/
├── SKILL.md
└── glossary_lookup.py
```

## Cross-references

- Glossary file: `translation/glossaries/glossary_ADVANCE_v1.json` (218 entries as of 2026-05-23).
- Glossary build tools (write path, not used by this skill): `translation/tools/build_glossary_from_docx.py`, `translation/scripts/build_glossary_json.py`.
- Used by: the maintainer (interactive), and the `/apply-reviewer-audit` skill's note_only_report.py uses the same JSON directly (does not invoke this skill).
