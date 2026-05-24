"""End-to-end pressure-test helper for the ADVANCE Qualtrics survey.

Embedded in /qualtrics-e2e-pressure-test skill. Provides the reusable
3-step CSV pull + production-pipeline feed + cleanup orchestration that
was repeated ~4× inline during Phase 4 of facility_address_first_plan.md.

Usage from the skill workflow (Claude pastes these calls inline as needed):

    from _e2e_helper import (
        pull_live_csv, find_rows_by_email_substring,
        feed_through_pipeline, delete_response,
    )

    rows = pull_live_csv()
    matched = find_rows_by_email_substring(rows, "f08@")
    pipeline_result = feed_through_pipeline(matched["F08"])
    delete_response(response_id)

Or as a CLI for ad-hoc inspection:

    python3 _e2e_helper.py csv-pull --email-substring f08@
    python3 _e2e_helper.py feed-pipeline --persona-id F08
    python3 _e2e_helper.py delete --response-id R_xxx

Note: this helper is sourced FROM the skill folder, not the project tools/
dir. It standalone-imports `email_draft_automation.qualtrics.*` so the
caller must be in a working environment where that import works (i.e.
the repo's venv with the ROOT_DIR on sys.path).
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests

SURVEY_ID = "SV_aWrEE8bXIdc6Pqe"


def _load_env_from(env_path: Path) -> None:
    if not env_path.exists():
        return
    export_re = re.compile(r"^export\s+([A-Z0-9_]+)=(.+)$")
    default_re = re.compile(r'^:\s*"\$\{([A-Z0-9_]+):=([^}]*)\}"\s*$')
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for pat in (export_re, default_re):
            m = pat.match(line)
            if m:
                os.environ.setdefault(m.group(1), m.group(2).strip().strip('"'))
                break


def _api_env() -> tuple[str, str]:
    """Return (base, token). Sources qualtrics_env.sh on demand if needed."""
    token = (os.environ.get("QUALTRICS_API_TOKEN") or "").strip()
    base = (os.environ.get("QUALTRICS_DATACENTER") or "").strip().rstrip("/")
    if not token or not base:
        # Try to locate qualtrics_env.sh by walking up from CWD.
        cur = Path.cwd()
        for parent in (cur, *cur.parents):
            candidate = parent / "qualtrics" / "qualtrics_env.sh"
            if candidate.exists():
                _load_env_from(candidate)
                break
        token = (os.environ.get("QUALTRICS_API_TOKEN") or "").strip()
        base = (os.environ.get("QUALTRICS_DATACENTER") or "").strip().rstrip("/")
    if not token or not base:
        sys.exit("ERROR: QUALTRICS_API_TOKEN + QUALTRICS_DATACENTER unset "
                 "(source qualtrics/qualtrics_env.sh)")
    return base, token


def pull_live_csv(*, retry_on_missing: Optional[str] = None,
                  wait_seconds: int = 15) -> list[dict]:
    """Pull the live Qualtrics CSV with useLabels=True. Returns a list of
    dicts keyed by DataExportTag column header (row 1 of the CSV).

    Each row dict has BOTH the DataExportTag name AND a synthesized
    `QID*_TEXT`-style key derived from the row 3 ImportId — so callers
    that use either lookup pattern work. This catches the iter 6 bug where
    `d.get('QID7_TEXT')` returned empty because the row 1 column was
    `f_ty_2_contact_email`.

    If retry_on_missing is set, this function pulls once; if the substring
    isn't found in any row's QID7_TEXT or f_ty_2_contact_email cell,
    waits `wait_seconds` and retries ONCE. Use this to handle the
    5-15s indexing lag after a fresh POST /responses.
    """
    base, token = _api_env()
    for attempt in (1, 2):
        rows = _pull_once(base, token)
        if not retry_on_missing or attempt == 2:
            return rows
        found = any(
            retry_on_missing in (
                (r.get("f_ty_2_contact_email") or r.get("QID7_TEXT") or "")
            )
            for r in rows
        )
        if found:
            return rows
        print(f"  [pull_live_csv] '{retry_on_missing}' not found, "
              f"waiting {wait_seconds}s + retry once...", file=sys.stderr)
        time.sleep(wait_seconds)
    return rows  # type: ignore[return-value]


def _pull_once(base: str, token: str) -> list[dict]:
    r = requests.post(
        f"{base}/surveys/{SURVEY_ID}/export-responses",
        headers={"X-API-TOKEN": token, "Content-Type": "application/json"},
        json={"format": "csv", "useLabels": True, "compress": True},
        timeout=60,
    )
    r.raise_for_status()
    prog_id = r.json()["result"]["progressId"]
    for _ in range(40):
        time.sleep(2)
        rp = requests.get(
            f"{base}/surveys/{SURVEY_ID}/export-responses/{prog_id}",
            headers={"X-API-TOKEN": token}, timeout=30,
        )
        rp.raise_for_status()
        status = rp.json()["result"]
        if status["status"] == "complete":
            file_id = status["fileId"]
            break
        if status["status"] == "failed":
            raise RuntimeError(f"export failed: {status}")
    else:
        raise TimeoutError("export polling exceeded 80s")
    rd = requests.get(
        f"{base}/surveys/{SURVEY_ID}/export-responses/{file_id}/file",
        headers={"X-API-TOKEN": token}, timeout=60,
    )
    rd.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(rd.content))
    csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
    with zf.open(csv_name) as f:
        text = io.TextIOWrapper(f, encoding="utf-8-sig")
        reader = csv.reader(text)
        h1 = next(reader)              # DataExportTag column names
        next(reader)                   # human-readable labels
        h3 = next(reader)              # JSON {"ImportId": "QID..."}
        # Build qid_aliases: position → QID-style key derived from h3
        qid_aliases: dict[int, str] = {}
        for i, meta in enumerate(h3):
            try:
                imp = (json.loads(meta) or {}).get("ImportId", "")
            except Exception:
                imp = ""
            if imp:
                qid_aliases[i] = imp
        out: list[dict] = []
        for row in reader:
            d: dict[str, str] = {}
            for i in range(min(len(h1), len(row))):
                d[h1[i]] = row[i]
                if i in qid_aliases and qid_aliases[i] != h1[i]:
                    d[qid_aliases[i]] = row[i]
            out.append(d)
    return out


def find_rows_by_email_substring(rows: list[dict],
                                 *substrings: str) -> dict[str, dict]:
    """Return {first-matching-substring: row} for rows whose
    `f_ty_2_contact_email` (or fallback `QID7_TEXT`) contains any substring.
    Useful for fishing test personas out of a CSV with hundreds of rows."""
    out: dict[str, dict] = {}
    for r in rows:
        em = (r.get("f_ty_2_contact_email") or r.get("QID7_TEXT") or "").strip()
        if not em:
            continue
        for s in substrings:
            if s in em and s not in out:
                out[s] = r
    return out


def feed_through_pipeline(csv_row: dict, *,
                          extra_synthetic: Optional[dict] = None) -> dict:
    """Run a single CSV-shape row through the production export pipeline.

    Returns {'f_ty_2_con': [...], 'list_rooms': [...]} dicts. Optional
    `extra_synthetic` overlays additional CSV keys (e.g. slot data) when
    the test row alone wouldn't produce a list_rooms row — honest because
    the persona's *change-under-test* fields are real, the synthetic
    overlay just provides ambient data the pipeline needs to materialize.

    The caller MUST be in a venv where email_draft_automation is importable
    (cwd inside the repo, ROOT_DIR.parent on sys.path)."""
    from email_draft_automation.qualtrics.export_responses_to_contacts import (
        build_f_ty2_rows_from_response, compute_list_rooms_rows,
        F_TY2_HEADER, LIST_ROOMS_HEADER,
    )
    from email_draft_automation.qualtrics.course_id_registry import CourseIdRegistry
    import tempfile

    if extra_synthetic:
        csv_row = {**csv_row, **extra_synthetic}

    f_ty2_rows = build_f_ty2_rows_from_response(csv_row, F_TY2_HEADER)
    with tempfile.TemporaryDirectory() as td:
        reg = CourseIdRegistry(Path(td) / "assignments.json")
        list_rooms = compute_list_rooms_rows(
            f_ty2_rows=f_ty2_rows,
            f_tor2_rows=[], f_tor3_rows=[],
            participant_rows=[],
            existing_header=LIST_ROOMS_HEADER,
            course_id_registry=reg,
        )
    return {"f_ty_2_con": f_ty2_rows, "list_rooms": list_rooms}


def delete_response(response_id: str) -> int:
    """DELETE a response. Returns HTTP status code. 200 = success.
    Always call in a finally block so cleanup happens even on assertion failure."""
    base, token = _api_env()
    r = requests.delete(
        f"{base}/surveys/{SURVEY_ID}/responses/{response_id}",
        headers={"X-API-TOKEN": token}, timeout=30,
    )
    return r.status_code


if __name__ == "__main__":
    # Minimal CLI for ad-hoc inspection
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("csv-pull")
    p1.add_argument("--email-substring", required=False)
    p2 = sub.add_parser("delete")
    p2.add_argument("--response-id", required=True)
    args = ap.parse_args()

    if args.cmd == "csv-pull":
        rows = pull_live_csv(retry_on_missing=args.email_substring or None)
        if args.email_substring:
            matched = find_rows_by_email_substring(rows, args.email_substring)
            print(json.dumps({k: {col: v[col] for col in v if v[col]}
                              for k, v in matched.items()},
                             indent=2, ensure_ascii=False))
        else:
            print(f"pulled {len(rows)} rows; first row keys: "
                  f"{list(rows[0].keys())[:10] if rows else []}")
    elif args.cmd == "delete":
        code = delete_response(args.response_id)
        print(f"DELETE {args.response_id}: {code}")
