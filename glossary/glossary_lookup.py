#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Look up a term in the ADVANCE glossary (FR/DE/EN).

The glossary is a JSON list of {src, tgt, english, definition, source_ref}
entries at ``translation/glossaries/glossary_ADVANCE_v1.json``. This script
runs four match passes (exact → substring → all-tokens → fuzzy fallback)
and pretty-prints results to stdout.

Used by the ``/glossary`` skill. Pure local lookup; no LLM, no writes.

Usage::

    python glossary_lookup.py <term> [--glossary PATH]
    python glossary_lookup.py "engagement social"
    python glossary_lookup.py accroché
    python glossary_lookup.py "Innere Balance"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_GLOSSARY = Path(
    "/Users/matthias/Library/CloudStorage/OneDrive-UniversitédeGenève/"
    "RA HORIZON/translation/glossaries/glossary_ADVANCE_v1.json"
)

# Articles to strip as a fallback (case-insensitive, with trailing space or apostrophe).
_ARTICLES = ("l'", "le ", "la ", "les ", "un ", "une ", "des ", "du ", "de ",
             "der ", "die ", "das ", "den ", "dem ", "ein ", "eine ", "einer ",
             "the ", "a ", "an ")

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    )


def _norm(s: str) -> str:
    """Lowercase + strip diacritics + collapse whitespace."""
    return re.sub(r"\s+", " ", _strip_diacritics(s).lower()).strip()


def _strip_article(s: str) -> str:
    low = s.lower()
    for art in _ARTICLES:
        if low.startswith(art):
            return s[len(art):].lstrip()
    return s


def _recency_key(source_ref: str) -> Tuple[int, str]:
    """Sort key: newer dates first, then alpha."""
    if not source_ref:
        return (0, "")
    m = _DATE_RE.search(source_ref)
    if m:
        # negative so newest is first when sorted ascending
        return (-int(m.group(1) + m.group(2) + m.group(3)), source_ref)
    return (0, source_ref)


def _entry_fields(e: Dict) -> Tuple[str, str, str]:
    return (e.get("src") or "", e.get("tgt") or "", e.get("english") or "")


def _exact_match(entries: List[Dict], term: str) -> List[Dict]:
    t = _norm(term)
    return [e for e in entries if any(_norm(f) == t for f in _entry_fields(e))]


def _substring_match(entries: List[Dict], term: str) -> List[Dict]:
    if len(term.strip()) < 3:
        return []
    t = _norm(term)
    return [e for e in entries if any(t in _norm(f) for f in _entry_fields(e))]


def _all_tokens_match(entries: List[Dict], term: str) -> List[Dict]:
    tokens = [_norm(tok) for tok in term.split() if len(tok) >= 2]
    if not tokens:
        return []
    hits = []
    for e in entries:
        haystack = " ".join(_norm(f) for f in _entry_fields(e))
        if all(tok in haystack for tok in tokens):
            hits.append(e)
    return hits


def _fuzzy_candidates(entries: List[Dict], term: str, k: int = 5) -> List[Dict]:
    t = _norm(term)
    scored: List[Tuple[float, Dict]] = []
    for e in entries:
        score = 0.0
        for f in _entry_fields(e):
            if not f:
                continue
            ratio = SequenceMatcher(None, t, _norm(f)).ratio()
            if ratio > score:
                score = ratio
        scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for score, e in scored[:k] if score >= 0.4]


def _search(entries: List[Dict], term: str) -> Tuple[str, List[Dict]]:
    """Returns (match_kind, results). Tries:
        exact → substring → all-tokens → article-stripped variants
        → fuzzy fallback.
    """
    for label, fn in (
        ("exact", _exact_match),
        ("substring", _substring_match),
        ("all-tokens", _all_tokens_match),
    ):
        hits = fn(entries, term)
        if hits:
            return label, hits

    # Retry with article stripped.
    stripped = _strip_article(term)
    if stripped != term:
        for label, fn in (
            ("exact (article-stripped)", _exact_match),
            ("substring (article-stripped)", _substring_match),
        ):
            hits = fn(entries, stripped)
            if hits:
                return label, hits

    return "fuzzy", _fuzzy_candidates(entries, term)


def _sort_by_recency(entries: List[Dict]) -> List[Dict]:
    return sorted(entries, key=lambda e: _recency_key(e.get("source_ref") or ""))


def _truncate(s: str, n: int) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _format_results(match_kind: str, hits: List[Dict], term: str) -> str:
    if not hits:
        return f"No matches for '{term}' (even fuzzy)."

    lines: List[str] = []
    if match_kind == "fuzzy":
        lines.append(
            f"No direct match for '{term}'. {len(hits)} closest candidate(s):"
        )
    else:
        lines.append(
            f"{len(hits)} match{'es' if len(hits) != 1 else ''} for '{term}' "
            f"(match: {match_kind})."
        )
    lines.append("")

    for i, e in enumerate(hits, 1):
        src = _truncate(e.get("src", ""), 60)
        tgt = _truncate(e.get("tgt", ""), 60)
        eng = _truncate(e.get("english", ""), 50)
        ref = _truncate(e.get("source_ref", ""), 60) or "—"
        lines.append(f"[{i}] FR: {src}")
        lines.append(f"    DE: {tgt}")
        lines.append(f"    EN: {eng}")
        lines.append(f"    src_ref: {ref}")
        defn = (e.get("definition") or "").strip()
        if defn:
            lines.append(f"    def: {_truncate(defn, 200)}")
        if e.get("hardcode"):
            lines.append(f"    hardcode: {e['hardcode']}")
        lines.append("")

    return "\n".join(lines).rstrip()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("term", help="FR, DE, or EN term to look up.")
    p.add_argument(
        "--glossary",
        type=Path,
        default=DEFAULT_GLOSSARY,
        help=f"Glossary JSON path. Default: {DEFAULT_GLOSSARY}",
    )
    args = p.parse_args(argv)

    if not args.glossary.exists():
        print(f"glossary not found: {args.glossary}", file=sys.stderr)
        return 2

    try:
        data = json.loads(args.glossary.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"failed to parse glossary: {e}", file=sys.stderr)
        return 2

    if isinstance(data, dict):
        entries = data.get("entries", [])
    else:
        entries = data
    if not isinstance(entries, list) or not entries:
        print("glossary is empty or malformed", file=sys.stderr)
        return 2

    match_kind, hits = _search(entries, args.term)
    hits = _sort_by_recency(hits)
    print(_format_results(match_kind, hits, args.term))
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
