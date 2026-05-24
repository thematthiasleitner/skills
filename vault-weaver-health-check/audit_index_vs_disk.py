#!/usr/bin/env python3
"""Compare vault-weaver's index.json against on-disk concept files.

Usage:
    audit_index_vs_disk.py --vault /path/to/vault [--format human|json]

Reports:
    - Per-status counts (disk + index)
    - Mismatches: file location disagrees with index status
    - Orphan index entries (slug in index, file missing)
    - Orphan files (file in concepts folder, no index entry)

Read-only. Never writes anything.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

SUBFOLDERS = ("approved", "pending", "rejected")
FM_KEYS = {
    "VW_status": re.compile(r"^VW_status:\s*(\S+)", re.MULTILINE),
    "VW_approved": re.compile(r"^VW_approved:\s*(\S+)", re.MULTILINE),
    "VW_rejected": re.compile(r"^VW_rejected:\s*(\S+)", re.MULTILINE),
    "VW_concept_slug": re.compile(r"^VW_concept_slug:\s*(\S+)", re.MULTILINE),
}


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def read_frontmatter(path: Path) -> Dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    block = text[4:end]
    out: Dict[str, str] = {}
    for key, pat in FM_KEYS.items():
        m = pat.search(block)
        if m:
            out[key] = m.group(1).strip().strip('"').strip("'")
    return out


def resolved_status(fm: Dict[str, str]) -> str | None:
    if fm.get("VW_status") in ("approved", "pending", "rejected"):
        return fm["VW_status"]
    rej = fm.get("VW_rejected", "").lower() in ("true", "yes")
    app = fm.get("VW_approved", "").lower() in ("true", "yes")
    if rej:
        return "rejected"
    if app:
        return "approved"
    return None


def scan_disk(concepts_root: Path) -> Dict[str, Dict]:
    """Returns dict[slug] = {path, subfolder, fm_status, displayName}."""
    out: Dict[str, Dict] = {}
    for sub in SUBFOLDERS:
        folder = concepts_root / sub
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            fm = read_frontmatter(md)
            slug = fm.get("VW_concept_slug") or slugify(md.stem)
            out[slug] = {
                "path": str(md),
                "subfolder": sub,
                "fm_status": resolved_status(fm) or "pending",
                "displayName": md.stem,
            }
    return out


def load_index(index_path: Path) -> Dict[str, Dict]:
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: cannot read index.json: {e}", file=sys.stderr)
        return {}
    nodes = raw.get("nodes") or raw.get("concepts") or {}
    if isinstance(nodes, list):
        nodes = {n.get("slug", str(i)): n for i, n in enumerate(nodes)}
    return nodes


def audit(disk: Dict[str, Dict], index: Dict[str, Dict]) -> Dict:
    mismatches: List[Dict] = []
    orphan_index: List[str] = []
    orphan_disk: List[str] = []

    for slug, info in disk.items():
        node = index.get(slug)
        if node is None:
            orphan_disk.append(slug)
            continue
        idx_status = node.get("status") or "pending"
        # Disk truth wins: file location is canonical
        if info["subfolder"] != idx_status:
            mismatches.append({
                "slug": slug,
                "disk_subfolder": info["subfolder"],
                "fm_status": info["fm_status"],
                "index_status": idx_status,
                "path": info["path"],
            })

    for slug in index:
        if slug not in disk:
            orphan_index.append(slug)

    return {
        "disk_counts": _count_by(disk, "subfolder"),
        "index_counts": _count_by_status(index),
        "mismatches": mismatches,
        "orphan_index": orphan_index,
        "orphan_disk": orphan_disk,
    }


def _count_by(items: Dict[str, Dict], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {"approved": 0, "pending": 0, "rejected": 0}
    for v in items.values():
        k = v.get(key, "pending")
        out[k] = out.get(k, 0) + 1
    return out


def _count_by_status(index: Dict[str, Dict]) -> Dict[str, int]:
    out: Dict[str, int] = {"approved": 0, "pending": 0, "rejected": 0}
    for node in index.values():
        s = node.get("status") or "pending"
        out[s] = out.get(s, 0) + 1
    return out


def render_human(report: Dict) -> str:
    dc, ic = report["disk_counts"], report["index_counts"]
    lines = []
    lines.append(f"Disk:   approved={dc['approved']:>5}  pending={dc['pending']:>5}  rejected={dc['rejected']:>5}  total={sum(dc.values())}")
    lines.append(f"Index:  approved={ic['approved']:>5}  pending={ic['pending']:>5}  rejected={ic['rejected']:>5}  total={sum(ic.values())}")
    n_mm = len(report["mismatches"])
    n_oi = len(report["orphan_index"])
    n_od = len(report["orphan_disk"])
    status = "in sync" if (n_mm + n_oi + n_od == 0) else f"{n_mm} mismatches, {n_oi} orphan-index, {n_od} orphan-disk"
    lines.append(f"Status: {status}")
    lines.append("")

    if n_mm:
        lines.append(f"== Mismatches ({n_mm}) ==")
        for m in report["mismatches"][:50]:
            lines.append(f"  {m['slug']:<40}  disk={m['disk_subfolder']:<9} fm={m['fm_status']:<9} index={m['index_status']}")
            lines.append(f"    {m['path']}")
        if n_mm > 50:
            lines.append(f"  ... and {n_mm - 50} more")
        lines.append("")
    if n_oi:
        lines.append(f"== Orphan index entries ({n_oi}) ==")
        for s in report["orphan_index"][:30]:
            lines.append(f"  {s}")
        if n_oi > 30:
            lines.append(f"  ... and {n_oi - 30} more")
        lines.append("")
    if n_od:
        lines.append(f"== Orphan files on disk ({n_od}) ==")
        for s in report["orphan_disk"][:30]:
            lines.append(f"  {s}")
        if n_od > 30:
            lines.append(f"  ... and {n_od - 30} more")
        lines.append("")
    if n_mm + n_oi + n_od == 0:
        lines.append("No anomalies detected.")
    else:
        lines.append("Recommendation:")
        if n_mm:
            lines.append("  - Open vault-weaver settings → Maintenance → \"Reconcile from frontmatter\" to align index to disk.")
        if n_oi:
            lines.append("  - Run \"Reconcile index ↔ disk\" to drop orphan index entries.")
        if n_od:
            lines.append("  - Orphan files may be pre-migration leftovers. Inspect a few and decide.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True, help="Path to vault root")
    ap.add_argument("--format", choices=("human", "json"), default="human")
    args = ap.parse_args()

    vault = Path(args.vault)
    concepts = vault / "0.Tags"
    index = vault / ".obsidian/plugins/vault-weaver/index.json"

    if not concepts.is_dir():
        print(f"ERROR: no concepts folder at {concepts}", file=sys.stderr)
        return 2
    if not index.is_file():
        print(f"ERROR: no index.json at {index}", file=sys.stderr)
        return 2

    disk = scan_disk(concepts)
    idx = load_index(index)
    report = audit(disk, idx)

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_human(report))

    has_issues = bool(report["mismatches"] or report["orphan_index"] or report["orphan_disk"])
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
