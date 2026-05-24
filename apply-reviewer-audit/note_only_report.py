#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surface skip_note_only rows from a reviewer-audit XLSX with glossary
suggestions.

A "note-only" row is one where the reviewer left a comment but no
correction — reviewer_certified=FALSE, reviewer_corrected_de empty,
reviewer_note non-empty. scripts/apply_reviewer_feedback.py classifies
these as ``skip_note_only`` and never writes them to the block store.

The skill /apply-reviewer-audit calls this script after the apply step
so Claude can decide per-row whether to surgically apply a glossary
canonical form OR fall back to a Gemini retranslate with the note as
judge-feedback.

Usage::

    python note_only_report.py <audit.xlsx> [--block-store-root PATH] \
                                            [--glossary PATH]

Output is JSON on stdout, one object per note-only row::

    {
      "file_sha8": "...",
      "block_id": "...",
      "status": "flagged"|"rejected"|...,
      "fr_text": "...",
      "de_text": "...",
      "reviewer_note": "...",
      "judge_verdict": "...",
      "judge_rationale": "...",
      "qc_summary": "...",
      "glossary_suggestions": [
        {"src": "<fr term>", "tgt": "<de term>", "english": "...",
         "definition": "...", "match_reason": "note|fr|de"}
      ]
    }

Glossary suggestions are best-effort string-match against
``glossaries/glossary_ADVANCE_v1.json`` (or the path passed via
``--glossary``). The skill MUST present the suggestions to the user
before any block-store write — never auto-apply.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import openpyxl  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "openpyxl not installed. Run from the translation/ venv: "
        "translation/.venv/bin/python ~/.claude/skills/apply-reviewer-audit/"
        "note_only_report.py ..."
    ) from e


_TRUE = {"TRUE", "T", "YES", "Y", "1", "X"}


def _is_true(v) -> bool:
    if v is True:
        return True
    if isinstance(v, str):
        return v.strip().upper() in _TRUE
    if isinstance(v, (int, float)):
        return v == 1
    return False


def _is_blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _read_audit_rows(xlsx_path: Path) -> List[Dict]:
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True, read_only=True)
    out: List[Dict] = []
    needed = (
        "file_sha8", "block_id",
        "reviewer_certified", "reviewer_corrected_de", "reviewer_note",
        "force_retranslate",
        "status", "fr_text", "de_text",
        "qc_summary", "judge_verdict", "judge_rationale",
    )
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        try:
            header = list(next(rows))
        except StopIteration:
            continue
        idx = {}
        for col in needed:
            try:
                idx[col] = header.index(col)
            except ValueError:
                idx[col] = None
        if idx["file_sha8"] is None or idx["block_id"] is None:
            continue  # not an audit sheet
        for row in rows:
            rec = {}
            for col, i in idx.items():
                rec[col] = row[i] if (i is not None and i < len(row)) else None
            if rec.get("file_sha8") and rec.get("block_id"):
                out.append(rec)
    return out


def _is_note_only(row: Dict) -> bool:
    if _is_true(row.get("force_retranslate")):
        return False
    cert = _is_true(row.get("reviewer_certified"))
    has_corr = not _is_blank(row.get("reviewer_corrected_de"))
    has_note = not _is_blank(row.get("reviewer_note"))
    return (not cert) and has_note and (not has_corr)


def _load_glossary(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        entries = data.get("entries")
        if isinstance(entries, list):
            return entries
    return []


def _glossary_suggestions(row: Dict, glossary: List[Dict]) -> List[Dict]:
    """Best-effort substring match.

    For each glossary entry, check whether its ``src`` or ``tgt`` (lowered)
    appears in the note, fr_text, or de_text. Cap suggestions at 5 per row
    so the report stays readable.
    """
    if not glossary:
        return []
    note = (row.get("reviewer_note") or "").lower()
    fr = (row.get("fr_text") or "").lower()
    de = (row.get("de_text") or "").lower()
    rationale = (row.get("judge_rationale") or "").lower()
    hay = {"note": note, "judge": rationale, "fr": fr, "de": de}
    hits: List[Dict] = []
    seen = set()
    for e in glossary:
        if not isinstance(e, dict):
            continue
        src = (e.get("src") or e.get("source") or "").strip()
        tgt = (e.get("tgt") or e.get("target") or "").strip()
        if not src or not tgt:
            continue
        src_low = src.lower()
        tgt_low = tgt.lower()
        match_reason = None
        for where, text in hay.items():
            if not text:
                continue
            if len(src_low) >= 3 and src_low in text:
                match_reason = f"src_in_{where}"
                break
            if len(tgt_low) >= 3 and tgt_low in text:
                match_reason = f"tgt_in_{where}"
                break
        if not match_reason:
            continue
        key = (src_low, tgt_low)
        if key in seen:
            continue
        seen.add(key)
        hits.append({
            "src": src,
            "tgt": tgt,
            "english": e.get("english") or "",
            "definition": (e.get("definition") or "")[:200],
            "source_ref": e.get("source_ref") or "",
            "match_reason": match_reason,
        })
        if len(hits) >= 5:
            break
    return hits


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("xlsx", type=Path)
    p.add_argument(
        "--glossary",
        type=Path,
        default=None,
        help="Glossary JSON path. Default: <xlsx-parent-dir>/../../glossaries/"
             "glossary_ADVANCE_v1.json",
    )
    args = p.parse_args(argv)

    if not args.xlsx.exists():
        print(f"audit XLSX not found: {args.xlsx}", file=sys.stderr)
        return 2

    if args.glossary is None:
        # Walk up looking for translation/glossaries/glossary_ADVANCE_v1.json
        candidate = None
        for parent in [args.xlsx.parent, *args.xlsx.parents]:
            g = parent / "glossaries" / "glossary_ADVANCE_v1.json"
            if g.exists():
                candidate = g
                break
        args.glossary = candidate or (args.xlsx.parent / "glossary.json")

    glossary = _load_glossary(args.glossary)
    rows = _read_audit_rows(args.xlsx)
    note_only = [r for r in rows if _is_note_only(r)]

    out = []
    for r in note_only:
        rec = {
            "file_sha8": r["file_sha8"],
            "block_id": r["block_id"],
            "status": r.get("status"),
            "fr_text": r.get("fr_text"),
            "de_text": r.get("de_text"),
            "reviewer_note": r.get("reviewer_note"),
            "judge_verdict": r.get("judge_verdict"),
            "judge_rationale": r.get("judge_rationale"),
            "qc_summary": r.get("qc_summary"),
            "glossary_suggestions": _glossary_suggestions(r, glossary),
        }
        out.append(rec)

    print(json.dumps({
        "audit_xlsx": str(args.xlsx),
        "glossary": str(args.glossary),
        "total_audit_rows": len(rows),
        "note_only_count": len(note_only),
        "rows": out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
