---
name: french-typography-nbsp
description: Detect and neutralize the U+00A0 (NBSP) trap when comparing French strings — subjects, titles, labels, glossary entries — against templates stored on disk. French typography mandates a non-breaking space before "high" punctuation (`:`, `?`, `!`, `;`, `»`), but JSON / YAML / code templates almost always use regular U+0020. Naive substring or equality match silently fails. Invoke whenever you're about to compare, search, or fuzzy-match French strings, ESPECIALLY against Outlook-sent message subjects, Qualtrics labels, or any user-typed FR content.
---

# French Typography NBSP — Whitespace Trap in String Matching

A 104-row misclassification bug in the ADVANCE `sent_log` backfill was traced to this one issue. The fix is two lines. Knowing about the trap is everything.

---

## The trap, by example

Template on disk (`consent_pre_reminder_1.json`):
```
"subject": "Rappel : Étude ADVANCE – formulaire de consentement et premier questionnaire"
                  ^
                  U+0020 (regular space)
```

Actual subject of the email Outlook actually sends to the participant:
```
"Rappel : Étude ADVANCE – formulaire de consentement et premier questionnaire"
        ^
        U+00A0 (NBSP)
```

Visually identical. Bytes differ. `subject_from_outlook.startswith(template_subject)` returns **False**. `template_subject in normalized_subject` returns **False**.

Outlook (and most modern mail clients on French locales) inserts NBSP automatically before `:`, `?`, `!`, `;` per French typography rules. Many template authors paste from Word, which also inserts NBSP. The JSON file may have either depending on how it was edited.

You will not see the difference in any editor that renders both as a space.

---

## The fix

Collapse all whitespace runs to a single regular space on BOTH sides before comparing:

```python
import re
_WS_RE = re.compile(r"\s+")

def normalize_for_match(s: str) -> str:
    """Lowercase + collapse any whitespace run (incl. NBSP) to single U+0020."""
    return _WS_RE.sub(" ", s or "").strip().lower()
```

`\s` in Python regex matches `[ \t\n\r\f\v]` AND Unicode-whitespace including U+00A0 (NBSP), U+2009 (thin space), U+202F (narrow no-break space), U+3000 (ideographic space), etc. One regex covers them all.

Apply to BOTH library entries and incoming strings before any substring / equality check:

```python
library_fixed = normalize_for_match(template_subject)
incoming      = normalize_for_match(outlook_subject)
if library_fixed in incoming:  # now matches
    ...
```

---

## When this trap is most likely to bite

- **Outlook / Gmail / Apple Mail FR subjects** vs JSON templates.
- **Qualtrics question/answer text** copy-pasted from Word docs vs assertions in tests / export rules.
- **Glossary lookup** of French source phrases that were authored in different tools.
- **Slack message search** with French keywords (less reliable but happens).
- **Filename matching** when filenames embed French phrases with `:` (rare but seen).

It bites especially hard on **`startswith` / `==` / `in`** style matches with **longer-fixed-segment-first** sort orders: if the longer (more specific) library entry contains NBSP and the incoming string doesn't (or vice versa), the matcher falls through to a shorter (less specific) entry and silently mis-classifies. That's exactly the ADVANCE failure mode — reminders with the `Rappel : …` prefix fell through to the next-shorter entry (the consent invite, no prefix) and 104 sends got tagged wrong.

---

## Detection checklist

When investigating a suspected NBSP issue:

```python
# Inspect bytes side-by-side
for i, ch in enumerate(suspect_string[:30]):
    print(f"  {i:2d}: {ch!r}  U+{ord(ch):04X}")
```

If you see `U+00A0` (NBSP), `U+2009` (thin space), or `U+202F` (narrow no-break space) anywhere — those bytes are the bug.

Also worth checking:
- `U+2013` (en dash `–`) vs `U+2014` (em dash `—`) vs `U+002D` (hyphen `-`)
- `U+2019` (right single quote `'`) vs `U+0027` (apostrophe `'`)
- `U+00C9` (`É`) appearing as `U+0045 U+0301` (decomposed NFD) — fix with `unicodedata.normalize("NFC", s)`.

---

## Generalising

For any cross-source string matching where French (or any language with high-punctuation NBSP — also Russian, Polish to a lesser extent) text crosses a system boundary, **always normalise whitespace + lowercase + NFC unicode-normalise before comparing**:

```python
import re, unicodedata
_WS_RE = re.compile(r"\s+")

def cross_source_normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = _WS_RE.sub(" ", s).strip().lower()
    return s
```

Apply on both sides at compare time, OR pre-normalise the library at load time and re-normalise incoming values on the hot path. Either works; the former is safer if the library is rebuilt frequently.

---

## Reference incident

ADVANCE `sent_log` backfill, 2026-05-26. Subjects like `"Rappel : Étude ADVANCE – formulaire…"` (NBSP after `Rappel`) were sent by Outlook from templates loaded from JSON files with regular spaces. The match library was sorted longest-first; the longer reminder entry didn't match (NBSP mismatch), so the matcher fell through to the shorter `consent_pre_invite` entry which had no `Rappel` prefix and DID match as a substring. Result: 104 reminder sends were classified as invites; participants showed as having received an invite but no reminder. Fixed by adding `_WS_RE.sub(" ", …)` in `_normalize_subject` and the library loader. Regression test: `tests/test_backfill_sent_log_history.py::test_match_subject_reminder_vs_invite_disambiguation`.
