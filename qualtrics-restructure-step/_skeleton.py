"""Phase {PHASE} iter {ITER}: {ONE_LINE_INTENT}

{LONGER_DESCRIPTION}

Idempotent: re-running on a survey that already has this change is a
no-op. Default mode is --dry-run (read-only); pass --apply to mutate.

Usage:
    cd email_draft_automation
    set -a && source qualtrics/qualtrics_env.sh && set +a
    .venv/bin/python3 tools/{SCRIPT_FILENAME}            # dry-run
    .venv/bin/python3 tools/{SCRIPT_FILENAME} --apply    # live mutation

Plan: docs/{PLAN_FILENAME}.md (Phase {PHASE}, iter {ITER}).
"""
from __future__ import annotations

import argparse
import json  # remove if not building DisplayLogic
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "qualtrics" / "qualtrics_env.sh"

SURVEY_ID = "SV_aWrEE8bXIdc6Pqe"

# ─── REPLACE: action-specific constants ─────────────────────────────────────
# Examples (uncomment + customise the one(s) you need):
#
# Single-target ADD_QUESTION / EDIT_QUESTION:
# TARGET_BLOCK_ID = "BL_xxxxxxxxx"
# NEW_TAG = "f_ty_addr_kind"
# INSERT_AFTER_QID = "QID182"
#
# Multi-target RENAME_TAG / DISPLAY_LOGIC:
# TARGETS = {
#     "QID34":  "f_ty_room_canton",     # qid → tag (for logging)
#     "QID12":  "f_ty_room_city",
#     ...
# }
#
# DISPLAY_LOGIC referencing another question:
# GATE_QID = "QID264"
# GATE_CHOICE = "1"   # SelectableChoice number for "Physical"
# ────────────────────────────────────────────────────────────────────────────


# ─── Standard env-load helpers (do not customise) ───────────────────────────


def _load_env() -> None:
    """Source qualtrics_env.sh so QUALTRICS_API_TOKEN + QUALTRICS_DATACENTER
    are populated. Idempotent — uses setdefault."""
    if not ENV_PATH.exists():
        return
    export_re = re.compile(r"^export\s+([A-Z0-9_]+)=(.+)$")
    default_re = re.compile(r'^:\s*"\$\{([A-Z0-9_]+):=([^}]*)\}"\s*$')
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for pat in (export_re, default_re):
            m = pat.match(line)
            if m:
                os.environ.setdefault(m.group(1), m.group(2).strip().strip('"'))
                break


def _env(name: str) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val:
        sys.exit(f"ERROR: missing env var {name} (source qualtrics_env.sh)")
    return val


# ─── Standard API helpers (use as-is; add more from existing scripts as needed) ─


def get_survey_definition(base: str, token: str) -> dict:
    r = requests.get(
        f"{base}/survey-definitions/{SURVEY_ID}",
        headers={"X-API-TOKEN": token}, timeout=60,
    )
    r.raise_for_status()
    return r.json()["result"]


def get_question(base: str, qid: str, token: str) -> dict:
    r = requests.get(
        f"{base}/survey-definitions/{SURVEY_ID}/questions/{qid}",
        headers={"X-API-TOKEN": token}, timeout=60,
    )
    r.raise_for_status()
    return r.json()["result"]


def get_block(base: str, block_id: str, token: str) -> dict:
    r = requests.get(
        f"{base}/survey-definitions/{SURVEY_ID}/blocks/{block_id}",
        headers={"X-API-TOKEN": token}, timeout=60,
    )
    r.raise_for_status()
    return r.json()["result"]


def put_question(base: str, qid: str, payload: dict, token: str) -> requests.Response:
    return requests.put(
        f"{base}/survey-definitions/{SURVEY_ID}/questions/{qid}",
        headers={"X-API-TOKEN": token, "Content-Type": "application/json"},
        json=payload, timeout=60,
    )


def put_block(base: str, block_id: str, payload: dict, token: str) -> requests.Response:
    return requests.put(
        f"{base}/survey-definitions/{SURVEY_ID}/blocks/{block_id}",
        headers={"X-API-TOKEN": token, "Content-Type": "application/json"},
        json=payload, timeout=60,
    )


def post_question(base: str, block_id: str, payload: dict, token: str) -> requests.Response:
    return requests.post(
        f"{base}/survey-definitions/{SURVEY_ID}/questions",
        headers={"X-API-TOKEN": token, "Content-Type": "application/json"},
        params={"blockId": block_id},
        json=payload, timeout=60,
    )


# ─── REPLACE: action-specific helpers ──────────────────────────────────────
# Common shapes (pick + adapt the one matching the mutation type):
#
# def build_payload() -> dict:
#     """For ADD_QUESTION — full Qualtrics question shape. Refer to the
#     `/qualtrics` skill for the canonical shape per QuestionType."""
#     return {...}
#
# def build_display_logic(...) -> dict:
#     """Pattern-match from tools/restructure_facility_step_6_zoom_display_logic.py
#     (single condition) or step_5c_slot_count_gating.py (OR of conditions).
#     Always uses QuestionIsInLoop="yes" + LoopAndMergeLoops="current" for
#     loop-block targets."""
#     return {...}
#
# def find_existing_qid_by_tag(definition: dict, tag: str) -> Optional[str]:
#     """Idempotency probe for ADD_QUESTION / RENAME_TAG."""
#     for qid, q in (definition.get("Questions") or {}).items():
#         if (q.get("DataExportTag") or "").strip() == tag:
#             return qid
#     return None
#
# def has_target_displaylogic(question: dict, gate_qid: str) -> bool:
#     """Idempotency probe for DISPLAY_LOGIC."""
#     dl = question.get("DisplayLogic")
#     return bool(dl) and gate_qid in json.dumps(dl)
# ────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--apply",
        action="store_true",
        help="Make real API calls. Default is dry-run (read-only).",
    )
    args = p.parse_args(argv)

    _load_env()
    token = _env("QUALTRICS_API_TOKEN")
    base = _env("QUALTRICS_DATACENTER").rstrip("/")

    print(f"Survey: {SURVEY_ID}")
    print(f"Mode  : {'APPLY (mutating)' if args.apply else 'DRY-RUN (read-only)'}")
    # print(f"Target: {TARGET_DESCRIPTION}")   # customise
    print()

    # ─── Step 1: idempotency probe ─────────────────────────────────────────
    # If the change is already applied, exit 0 silently.
    print("[step 1/N] Fetching survey definition (idempotency probe)...")
    # definition = get_survey_definition(base, token)
    # if already_done(definition):
    #     print("[skip] Already applied. No-op.")
    #     return 0

    # ─── Step 2: planning ──────────────────────────────────────────────────
    # Build the planned changes WITHOUT mutating.
    # Print exactly what would be sent so the human can review.
    print("[step 2/N] Planning changes...")
    # to_apply: list[tuple[str, dict]] = []   # each entry = (description, payload)
    # for ...:
    #     to_apply.append((description, payload))
    #     print(f"  [plan] {description}")

    # ─── Step 3: dry-run early exit ────────────────────────────────────────
    if not args.apply:
        print()
        print("=== summary (dry-run) ===")
        # print(f"  would apply {len(to_apply)} change(s)")
        print("  re-run with --apply to perform the API calls")
        return 0

    # ─── Step 4: apply with per-op failure tracking ────────────────────────
    print()
    print("[step 4/N] APPLYING — per-op tracking...")
    failures: list[tuple[str, str]] = []
    # for description, payload in to_apply:
    #     r = put_question(base, qid, payload, token)   # or post / put_block
    #     if not r.ok:
    #         failures.append((description, f"{r.status_code} {r.text[:200]}"))
    #         print(f"  FAIL {description}: {r.status_code} {r.text[:120]}")
    #     else:
    #         print(f"  done {description}")

    # ─── Step 5: final summary ─────────────────────────────────────────────
    print()
    print("=== summary (applied) ===")
    # print(f"  updated: {len(to_apply) - len(failures)} of {len(to_apply)}")
    # print(f"  failed : {len(failures)}")
    if failures:
        print()
        print("FAILURES:")
        for desc, err in failures:
            print(f"  {desc}: {err}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
