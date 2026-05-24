#!/usr/bin/env python3
"""Analyse the vault-weaver activity log for anomalies.

Usage:
    analyze_activity_log.py --log /path/to/activity.log [--since 24h|7d|all] [--format human|json]

Detects:
    - Ping-pongs (same slug moved between subfolders within < 5s, 2+ times)
    - Error clusters (same error message 3+ times)
    - Lifecycle imbalances (ratio out of healthy band)
    - Tick performance (median, p95, max — flags ticks > 10s as UI-freeze risk)

Robust to missing log file and to unknown line formats — unparseable lines
are simply ignored.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Tolerant patterns. Activity log line shape evolved several times; match
# what we can and ignore what we can't.
TIMESTAMP_RE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\]?")
MOVE_RE = re.compile(r"(?:moved|→|->|reconcile)\s+(?P<slug>[\w-]+).*?(?P<from>approved|pending|rejected)\s*(?:→|->|to)\s*(?P<to>approved|pending|rejected)", re.IGNORECASE)
ERROR_RE = re.compile(r"\b(error|failed|warn|warning)\b[:\s]+(.{10,200})", re.IGNORECASE)
TICK_RE = re.compile(r"tick.*?(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE)


def parse_since(spec: str) -> datetime | None:
    if spec == "all":
        return None
    m = re.match(r"(\d+)([hdwm])$", spec)
    if not m:
        raise SystemExit(f"bad --since: {spec} (use NNh / NNd / NNw / all)")
    n, unit = int(m.group(1)), m.group(2)
    delta = {"h": timedelta(hours=n), "d": timedelta(days=n),
             "w": timedelta(weeks=n), "m": timedelta(minutes=n)}[unit]
    return datetime.now(timezone.utc) - delta


def parse_ts(s: str) -> datetime | None:
    # Tolerate "2026-05-24T12:34:56", "2026-05-24 12:34:56", trailing Z, ms.
    s = s.rstrip("Z")
    s = s.replace(" ", "T")
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def analyse(lines: List[str], since: datetime | None) -> Dict:
    moves: List[Dict] = []      # {ts, slug, from, to}
    errors: List[str] = []
    tick_ms: List[float] = []
    total_lines = 0

    for raw in lines:
        total_lines += 1
        ts_m = TIMESTAMP_RE.match(raw)
        ts = parse_ts(ts_m.group(1)) if ts_m else None
        if since and ts and ts < since:
            continue

        mv = MOVE_RE.search(raw)
        if mv:
            moves.append({
                "ts": ts,
                "slug": mv.group("slug"),
                "from": mv.group("from").lower(),
                "to": mv.group("to").lower(),
            })

        err = ERROR_RE.search(raw)
        if err:
            errors.append(err.group(2).strip())

        tk = TICK_RE.search(raw)
        if tk:
            try:
                tick_ms.append(float(tk.group(1)))
            except ValueError:
                pass

    return {
        "total_lines": total_lines,
        "ping_pongs": find_ping_pongs(moves),
        "error_clusters": cluster_errors(errors),
        "lifecycle_balance": lifecycle_balance(moves),
        "tick_stats": tick_stats(tick_ms),
        "moves_total": len(moves),
        "errors_total": len(errors),
    }


def find_ping_pongs(moves: List[Dict]) -> List[Dict]:
    """A ping-pong = the same slug moved 2+ times within < 5s with at least
    one direction reversal."""
    by_slug: Dict[str, List[Dict]] = defaultdict(list)
    for mv in moves:
        by_slug[mv["slug"]].append(mv)
    out: List[Dict] = []
    for slug, events in by_slug.items():
        events_with_ts = [e for e in events if e["ts"] is not None]
        events_with_ts.sort(key=lambda e: e["ts"])
        if len(events_with_ts) < 2:
            continue
        for i in range(1, len(events_with_ts)):
            a, b = events_with_ts[i - 1], events_with_ts[i]
            gap = (b["ts"] - a["ts"]).total_seconds()
            if gap < 5 and a["to"] == b["from"] and a["from"] == b["to"]:
                out.append({
                    "slug": slug,
                    "gap_seconds": round(gap, 2),
                    "path": f"{a['from']} → {a['to']} → {b['to']}",
                    "ts": a["ts"].isoformat() if a["ts"] else None,
                })
    return out


def cluster_errors(errors: List[str]) -> List[Tuple[str, int]]:
    # Normalise: strip slug-like tokens so identical errors with different
    # slugs cluster together.
    norm = [re.sub(r"\b[\w-]{8,}\b", "<TOKEN>", e) for e in errors]
    counts = Counter(norm)
    return [(msg, n) for msg, n in counts.most_common() if n >= 3]


def lifecycle_balance(moves: List[Dict]) -> Dict:
    # Net flow into each subfolder over the window.
    flow: Counter = Counter()
    for mv in moves:
        flow[mv["to"]] += 1
        flow[mv["from"]] -= 1
    return dict(flow)


def tick_stats(tick_ms: List[float]) -> Dict:
    if not tick_ms:
        return {"count": 0}
    return {
        "count": len(tick_ms),
        "median_ms": round(statistics.median(tick_ms), 1),
        "p95_ms": round(_percentile(tick_ms, 95), 1),
        "max_ms": round(max(tick_ms), 1),
        "slow_ticks_over_10s": sum(1 for ms in tick_ms if ms > 10_000),
    }


def _percentile(data: List[float], p: int) -> float:
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def render_human(report: Dict) -> str:
    lines = []
    lines.append(f"Activity log: {report['total_lines']} lines scanned, {report['moves_total']} moves, {report['errors_total']} errors")
    lines.append("")

    ts = report["tick_stats"]
    if ts.get("count"):
        flag = " ⚠ SLOW" if ts.get("slow_ticks_over_10s", 0) else ""
        lines.append(f"Ticks: {ts['count']}  median={ts['median_ms']}ms  p95={ts['p95_ms']}ms  max={ts['max_ms']}ms{flag}")
        if ts.get("slow_ticks_over_10s"):
            lines.append(f"  {ts['slow_ticks_over_10s']} tick(s) > 10s — UI freeze risk. Add yields in long loops.")
        lines.append("")

    pp = report["ping_pongs"]
    if pp:
        lines.append(f"== Ping-pongs ({len(pp)}) ==")
        for p in pp[:20]:
            lines.append(f"  {p['slug']:<30}  {p['path']}  (gap {p['gap_seconds']}s @ {p['ts']})")
        if len(pp) > 20:
            lines.append(f"  ... and {len(pp) - 20} more")
        lines.append("  → Likely a live-handler / sorter feedback loop. Check that the modify handler")
        lines.append("    early-exits when target folder matches index status.")
        lines.append("")
    else:
        lines.append("Ping-pongs: 0 ✅")

    ec = report["error_clusters"]
    if ec:
        lines.append(f"== Error clusters (≥3 occurrences) ==")
        for msg, n in ec[:10]:
            lines.append(f"  [{n}×] {msg[:160]}")
        lines.append("")
    else:
        lines.append("Error clusters: 0 ✅")

    bal = report["lifecycle_balance"]
    if bal:
        signs = lambda v: f"+{v}" if v > 0 else str(v)
        parts = [f"{k}={signs(v)}" for k, v in sorted(bal.items())]
        lines.append(f"Net lifecycle flow this window: {' '.join(parts)}")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--since", default="24h", help="24h | 7d | 30m | all")
    ap.add_argument("--format", choices=("human", "json"), default="human")
    args = ap.parse_args()

    log = Path(args.log)
    if not log.is_file():
        print(f"NOTE: no activity log at {log} (skill emits this when log absent)", file=sys.stderr)
        return 0

    since = parse_since(args.since)
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    report = analyse(lines, since)

    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_human(report))

    has_issues = bool(report["ping_pongs"] or report["error_clusters"]
                      or report["tick_stats"].get("slow_ticks_over_10s"))
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
