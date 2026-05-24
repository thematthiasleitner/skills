"""Live ADVANCE Qualtrics CSV pull helper. Read-only.

Embedded in /qualtrics-csv-pull skill. Standalone — no dependency on
email_draft_automation imports (unlike _e2e_helper.py from the e2e-test
skill, which does need the project's dispatch code).

Returns dicts keyed by both DataExportTag column names AND QID-based
ImportId aliases, so callers using either pattern work.

CLI:
    python3 _csv_pull.py                                         # 1-line summary
    python3 _csv_pull.py --email-substring "f08@"                # find matching rows
    python3 _csv_pull.py --email-substring "f08@" --columns "1_f_ty_addr_kind,1_f_ty_room_canton"
    python3 _csv_pull.py --response-id R_xxx                     # by exact RID

Python import:
    from _csv_pull import pull_live_csv, find_rows_by_email_substring,
                          find_row_by_response_id
"""
from __future__ import annotations

import argparse
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
    token = (os.environ.get("QUALTRICS_API_TOKEN") or "").strip()
    base = (os.environ.get("QUALTRICS_DATACENTER") or "").strip().rstrip("/")
    if not token or not base:
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
    """Pull the live ADVANCE Qualtrics CSV.

    Returns list of dicts keyed by row 1 DataExportTag column names + row 3
    ImportId QID-based aliases (both keys point to the same value, so
    callers using either pattern work).

    If retry_on_missing is set, pulls once; if the substring isn't found
    in any row's `f_ty_2_contact_email` or `QID7_TEXT` field, waits
    `wait_seconds` and retries once. Useful right after a fresh
    POST /responses to handle 5-15s indexing lag.
    """
    base, token = _api_env()
    for attempt in (1, 2):
        rows = _pull_once(base, token)
        if not retry_on_missing or attempt == 2:
            return rows
        found = any(
            retry_on_missing in (
                r.get("f_ty_2_contact_email") or r.get("QID7_TEXT") or ""
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
        h1 = next(reader)              # DataExportTag
        next(reader)                   # human labels
        h3 = next(reader)              # ImportId JSON
        qid_aliases: dict[int, str] = {}
        for i, meta in enumerate(h3):
            try:
                imp = (json.loads(meta) or {}).get("ImportId", "")
            except Exception:
                imp = ""
            if imp and imp != h1[i] if i < len(h1) else True:
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
    """Return {substring: first-matching-row}. Lookups via
    `f_ty_2_contact_email` falling back to `QID7_TEXT` falling back to
    `RecipientEmail` (for participant-side rows)."""
    out: dict[str, dict] = {}
    for r in rows:
        em = (
            r.get("f_ty_2_contact_email")
            or r.get("QID7_TEXT")
            or r.get("RecipientEmail", "")
        ).strip()
        if not em:
            continue
        for s in substrings:
            if s in em and s not in out:
                out[s] = r
    return out


def find_row_by_response_id(rows: list[dict], rid: str) -> Optional[dict]:
    for r in rows:
        if r.get("ResponseId") == rid:
            return r
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--email-substring",
                   help="Find rows whose contact email contains this string.")
    p.add_argument("--response-id", help="Find row by exact ResponseId.")
    p.add_argument("--columns",
                   help="Comma-separated column names to print "
                        "(default: print full row as JSON).")
    p.add_argument("--retry-on-missing", action="store_true",
                   help="If --email-substring is set, retry once after 15s if "
                        "the substring is missing (handles fresh-submission lag).")
    args = p.parse_args()

    retry = args.email_substring if args.retry_on_missing else None
    rows = pull_live_csv(retry_on_missing=retry)
    print(f"pulled {len(rows)} CSV rows", file=sys.stderr)

    columns = args.columns.split(",") if args.columns else None

    if args.response_id:
        row = find_row_by_response_id(rows, args.response_id)
        if not row:
            print(f"no row for ResponseId {args.response_id!r}")
            return 1
        _print_row(row, columns)
        return 0

    if args.email_substring:
        matched = find_rows_by_email_substring(rows, args.email_substring)
        if not matched:
            print(f"no rows matching {args.email_substring!r}")
            return 1
        for sub, row in matched.items():
            print(f"=== {sub} ===")
            _print_row(row, columns)
        return 0

    print(f"first row keys: {list(rows[0].keys())[:10] if rows else []}")
    return 0


def _print_row(row: dict, columns: Optional[list[str]]) -> None:
    if columns is None:
        # Only non-empty cells, sorted
        keep = {k: v for k, v in sorted(row.items()) if v}
        print(json.dumps(keep, indent=2, ensure_ascii=False))
    else:
        for c in columns:
            print(f"  {c} = {row.get(c, '')!r}")


if __name__ == "__main__":
    sys.exit(main())
