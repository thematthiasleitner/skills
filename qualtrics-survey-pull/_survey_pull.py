#!/usr/bin/env python3
"""Pull the live ADVANCE Qualtrics survey DEFINITION (questions/blocks/flow) as JSON.

Sibling to qualtrics-csv-pull (which pulls response *data*). Read-only.

Self-contained: reads the env vars directly, so it does NOT import the heavy
export_responses_to_contacts module (no side effects, no clone-path coupling).

Env (from `source qualtrics/qualtrics_env.sh`):
  QUALTRICS_API_TOKEN   — required
  QUALTRICS_DATACENTER  — the FULL base URL, e.g. https://fra1.qualtrics.com/API/v3
                          (this is the #1 gotcha: it is NOT just "fra1" — do not
                          re-prefix it with https:// or you get a double-scheme URL)
  QUALTRICS_BASE_URL    — optional alias for the base URL
  QUALTRICS_SURVEY_ID   — optional, defaults to SV_aWrEE8bXIdc6Pqe

CLI:
  _survey_pull.py                      # pull, save dated JSON, print summary
  _survey_pull.py --no-save            # pull, summary only, don't write a file
  _survey_pull.py --tag part_zoom      # pull + report one question by DataExportTag
  _survey_pull.py --tag f_ty_room_N_t1_begin --no-save
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import requests  # bundles certifi; system Python's urllib fails SSL verify against fra1

DEFAULT_SURVEY_ID = "SV_aWrEE8bXIdc6Pqe"


def _base_url() -> str:
    raw = (os.environ.get("QUALTRICS_BASE_URL")
           or os.environ.get("QUALTRICS_DATACENTER")
           or "").strip().rstrip("/")
    if not raw:
        raise SystemExit("Set QUALTRICS_DATACENTER (full base URL) — source qualtrics/qualtrics_env.sh first.")
    # GOTCHA: the env var is already a full URL. Only build one if a bare
    # datacenter id (e.g. "fra1") was supplied.
    if raw.startswith("http"):
        return raw
    return f"https://{raw}.qualtrics.com/API/v3"


def pull_survey_definition(survey_id: str | None = None) -> dict:
    """GET /survey-definitions/{id} → the `result` object (Questions/Blocks/SurveyFlow…)."""
    token = os.environ.get("QUALTRICS_API_TOKEN")
    if not token:
        raise SystemExit("Set QUALTRICS_API_TOKEN — source qualtrics/qualtrics_env.sh first.")
    sid = survey_id or os.environ.get("QUALTRICS_SURVEY_ID") or DEFAULT_SURVEY_ID
    url = f"{_base_url()}/survey-definitions/{sid}"
    resp = requests.get(url, headers={"X-API-TOKEN": token}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("result", {})


# ── Query helpers (work on the `result` dict) ───────────────────────────────

def question_by_tag(result: dict, tag: str) -> tuple[str, dict] | None:
    """Return (QID, question) whose DataExportTag == tag (case-insensitive)."""
    for qid, q in result.get("Questions", {}).items():
        if str(q.get("DataExportTag", "")).lower() == tag.lower():
            return qid, q
    return None


def block_of_question(result: dict, qid: str) -> str | None:
    for bid, b in result.get("Blocks", {}).items():
        for el in b.get("BlockElements", []):
            if el.get("Type") == "Question" and el.get("QuestionID") == qid:
                return bid
    return None


def blocks_in_flow(result: dict) -> set[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            if node.get("Type") == "Block" and node.get("ID"):
                found.add(node["ID"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(result.get("SurveyFlow", {}))
    return found


def question_report(result: dict, tag: str) -> dict:
    """One question's liveness/format snapshot — the thing column audits need."""
    hit = question_by_tag(result, tag)
    if not hit:
        return {"tag": tag, "found": False}
    qid, q = hit
    bid = block_of_question(result, qid)
    val = q.get("Validation", {}).get("Settings", {})
    return {
        "tag": tag, "found": True, "qid": qid,
        "type": f"{q.get('QuestionType')}/{q.get('Selector')}/{q.get('SubSelector')}",
        "block": bid or "<NO BLOCK — orphaned/dead>",
        "in_flow": (bid in blocks_in_flow(result)) if bid else False,
        "validation": {k: val.get(k) for k in ("Type", "ContentType", "ValidDateType", "ForceResponse") if k in val},
        "question_text": (q.get("QuestionText", "") or "")[:160],
    }


def _summary(result: dict) -> str:
    Q = result.get("Questions", {})
    B = result.get("Blocks", {})
    in_block = {el.get("QuestionID")
                for b in B.values() for el in b.get("BlockElements", [])
                if el.get("Type") == "Question"}
    orphaned = [q.get("DataExportTag") for qid, q in Q.items() if qid not in in_block]
    lines = [
        f"name: {result.get('SurveyName')}",
        f"questions: {len(Q)}   blocks: {len(B)}   blocks_in_flow: {len(blocks_in_flow(result))}",
        f"orphaned questions (in NO block → dead): {len(orphaned)}",
    ]
    if orphaned:
        lines.append("  " + ", ".join(sorted(t for t in orphaned if t))[:400])
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--survey-id")
    ap.add_argument("--tag", help="report one question by DataExportTag")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--out-dir", default="qualtrics", help="dir to save dated JSON (default: qualtrics)")
    args = ap.parse_args()

    result = pull_survey_definition(args.survey_id)
    if not args.no_save:
        stamp = datetime.now().strftime("%Y-%m-%d_%H.%M")
        dest = Path(args.out_dir) / f"ADVANCE_recruitment_definition_{stamp}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        json.dump({"result": result}, dest.open("w"), ensure_ascii=False, indent=1)
        print(f"saved -> {dest}")
    print(_summary(result))
    if args.tag:
        print("\n" + json.dumps(question_report(result, args.tag), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
