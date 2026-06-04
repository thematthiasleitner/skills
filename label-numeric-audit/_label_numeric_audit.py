#!/usr/bin/env python3
"""Audit ADVANCE code for NUMERIC assumptions on a label-based CSV (ADR 0003).

The export pulls `useLabels=True`, so CSV fields arrive as TEXT (`Survey Preview`,
not `1`). Any code that compares a CSV-sourced field to a numeric code, or reads
the raw CSV without the shared parser, is a latent bug. This greps for the three
antipatterns. Read-only — reports file:line + reason, fixes nothing.

Run from inside email_draft_automation:
  _label_numeric_audit.py
  _label_numeric_audit.py --globs 'qualtrics/*.py' 'src/*.py' 'tools/*.py'
"""
from __future__ import annotations

import argparse
import glob
import re

DEFAULT_GLOBS = ["qualtrics/*.py", "src/*.py"]

# Fields known to arrive as label TEXT (not numeric) under useLabels=True.
TEXT_FIELDS = ["Status", "Finished", "DistributionChannel"]

PATTERNS = [
    # (severity, compiled regex, reason). Each matches a single source line.
    ("HIGH", re.compile(r"\.get\(\s*['\"]Status['\"]\s*\).{0,40}==\s*['\"]\d+['\"]", re.I),
     "Status compared to a NUMERIC literal, but Status is TEXT ('Survey Preview') under "
     "useLabels=True → comparison is DEAD. Route through normalize_status() or compare the label."),
    # `\bstatus\b` (case-insensitive) catches a local var named `status` too, but the
    # trailing \b means it will NOT match `status_target` / `status_by_rid` (the `_` is a word char).
    # The `.{0,30}` gap bridges `.get("Status", "") == "1"`.
    ("HIGH", re.compile(r"\bstatus\b.{0,30}==\s*['\"]\d+['\"]", re.I),
     "status == numeric code — dead under label export (Status is text). Use is_live_response()/normalize_status()."),
    ("HIGH", re.compile(r"\bint\(\s*[^)]*\bStatus\b"),
     "int() on a Status field — it's a text label; int() will throw or mis-coerce."),
    ("REVIEW", re.compile(r"csv\.DictReader"),
     "csv.DictReader — IF this reads the Qualtrics RESPONSE export it bypasses read_csv_from_zip "
     "(won't strip the 3 header rows → 2 phantom rows). Harmless for unrelated local CSVs — verify the source."),
]

# Lines that are FINE even though they touch Status (the canonical chokepoint).
SAFE_HINT = re.compile(r"normalize_status|_STATUS_LABEL_TO_NUM|is_live_response|is_preview")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--globs", nargs="*", default=DEFAULT_GLOBS)
    args = ap.parse_args()

    findings: list[tuple[str, str, int, str, str]] = []
    for g in args.globs:
        for fp in sorted(glob.glob(g)):
            try:
                lines = open(fp, encoding="utf-8").read().splitlines()
            except Exception:  # noqa: BLE001
                continue
            for n, line in enumerate(lines, 1):
                if SAFE_HINT.search(line):
                    continue  # routed through the tolerant chokepoint — OK
                for sev, rx, reason in PATTERNS:
                    if rx.search(line):
                        findings.append((sev, fp, n, line.strip()[:100], reason))
                        break

    print("=== label-numeric audit (ADR 0003: CSV is label-based) ===")
    print(f"scanned: {args.globs}\n")
    if not findings:
        print("✅ no numeric-assumption antipatterns found.")
        return
    for sev in ("HIGH", "REVIEW"):
        bucket = [f for f in findings if f[0] == sev]
        if not bucket:
            continue
        print(f"── {sev} ({len(bucket)}) " + "─" * 40)
        for _, fp, n, src, reason in bucket:
            mark = "⛔" if sev == "HIGH" else "🔎"
            print(f"{mark} {fp}:{n}\n      {src}\n      → {reason}\n")
    print(f"{len(findings)} finding(s): {sum(1 for f in findings if f[0]=='HIGH')} HIGH, "
          f"{sum(1 for f in findings if f[0]=='REVIEW')} REVIEW. "
          "Fix HIGH: compare the label via normalize_status()/is_live_response(). "
          "REVIEW: confirm the DictReader target is/ isn't the Qualtrics export.")


if __name__ == "__main__":
    main()
