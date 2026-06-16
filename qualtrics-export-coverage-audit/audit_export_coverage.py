#!/usr/bin/env python3
"""Report Qualtrics DataExportTags that will NOT appear in CSV exports.

A question exports to CSV iff it is a member of a block AND that block is
reachable in the SurveyFlow. A *block-less* question (in no block's
BlockElements) is still "alive" in the definition but silently omitted from
every export — the failure mode behind the 2026-06 ADVANCE f_ty_room_N_t*
slot-column vanish. A question in a block not referenced by the flow likewise
never exports.

Read-only. Exits non-zero if any tagged question won't export (minus the
--expect-missing whitelist), so it doubles as a CI / Layer-C gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _unwrap(doc: dict) -> dict:
    """Accept either the raw survey-definition `result` object or a full
    {"result": …} API response."""
    if "result" in doc and isinstance(doc["result"], dict) and "Questions" in doc["result"]:
        return doc["result"]
    return doc


def _flow_block_ids(node: Any, acc: set[str]) -> set[str]:
    """Collect every Block ID referenced anywhere in the SurveyFlow tree.

    Block flow elements carry their target as `ID` with Type in
    {Block, Standard}; we walk the whole structure defensively (nested
    Branch/Group elements) and grab any Block-typed node's ID.
    """
    if isinstance(node, dict):
        if node.get("Type") in ("Block", "Standard") and isinstance(node.get("ID"), str):
            acc.add(node["ID"])
        for v in node.values():
            _flow_block_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            _flow_block_ids(v, acc)
    return acc


def audit(survey_def: dict, prefix: str = "") -> list[dict]:
    """Return a list of {qid, tag, reason} for every tagged question that
    will NOT export. `reason` ∈ {"block-less", "block <bid> not in flow"}."""
    result = _unwrap(survey_def)
    questions = result.get("Questions") or {}
    blocks = result.get("Blocks") or {}
    flow = result.get("SurveyFlow") or {}

    # qid -> block id it belongs to (first wins; a question is normally in one)
    qid_block: dict[str, str] = {}
    for bid, b in blocks.items():
        for el in (b.get("BlockElements") or []):
            if el.get("Type") == "Question" and el.get("QuestionID"):
                qid_block.setdefault(el["QuestionID"], bid)

    flow_blocks = _flow_block_ids(flow, set())

    problems: list[dict] = []
    for qid, q in questions.items():
        tag = q.get("DataExportTag") or ""
        if not tag:
            continue
        if prefix and not tag.startswith(prefix):
            continue
        bid = qid_block.get(qid)
        if bid is None:
            problems.append({"qid": qid, "tag": tag, "reason": "block-less"})
        elif bid not in flow_blocks:
            problems.append({"qid": qid, "tag": tag,
                             "reason": f"block {bid} not in flow"})
    problems.sort(key=lambda p: p["tag"])
    return problems


def _pull_live(survey_id: str) -> dict:
    import requests
    token = (os.environ.get("QUALTRICS_API_TOKEN") or "").strip()
    base = (os.environ.get("QUALTRICS_DATACENTER") or "").rstrip("/")
    if not token or not base:
        sys.exit("QUALTRICS_API_TOKEN / QUALTRICS_DATACENTER unset "
                 "(source qualtrics/qualtrics_env.sh)")
    r = requests.get(f"{base}/survey-definitions/{survey_id}",
                     headers={"X-API-TOKEN": token}, timeout=60)
    r.raise_for_status()
    return r.json()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", help="path to a saved survey-definition JSON")
    src.add_argument("--survey", help="survey ID to pull live (needs env)")
    ap.add_argument("--prefix", default="",
                    help="only audit DataExportTags with this prefix")
    ap.add_argument("--expect-missing", default="",
                    help="comma-separated tags known to be intentionally "
                         "non-exporting; reported but don't affect exit code")
    args = ap.parse_args(argv)

    if args.json:
        with open(args.json, encoding="utf-8") as fh:
            doc = json.load(fh)
    else:
        doc = _pull_live(args.survey)

    problems = audit(doc, prefix=args.prefix)
    expected = {t.strip() for t in args.expect_missing.split(",") if t.strip()}

    if not problems:
        scope = f" (prefix '{args.prefix}')" if args.prefix else ""
        print(f"PASS — every tagged question exports{scope}.")
        return 0

    unexpected = [p for p in problems if p["tag"] not in expected]
    for p in problems:
        mark = "  (expected)" if p["tag"] in expected else ""
        print(f"WON'T EXPORT  {p['tag']:34} {p['qid']:14} {p['reason']}{mark}")

    if unexpected:
        print(f"\nFAIL — {len(unexpected)} tag(s) silently dropped from CSV "
              "export (not in --expect-missing).")
        return 1
    print(f"\nPASS — all {len(problems)} non-exporting tag(s) are expected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
