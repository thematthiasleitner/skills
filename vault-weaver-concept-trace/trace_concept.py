#!/usr/bin/env python3
"""Single-slug end-to-end inspector for a Vault Weaver concept.

Usage:
    trace_concept.py --vault PATH --query STR              # resolve query → list candidates
    trace_concept.py --vault PATH --slug SLUG [--format human|json] [--all]

Output (human format): a one-page report covering disk state, index state,
inbound wikilinks across the vault, the activity-log timeline for this slug,
and a rule-based diagnosis line.

Read-only. Never writes anywhere.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUBFOLDERS = ("approved", "pending", "rejected")
WIKILINK_RE = re.compile(r"\[\[([^\[\]\|]+?)(\|[^\[\]]+?)?\]\]")
CALLOUT_RE = re.compile(r"^>\s*\[!", re.MULTILINE)
TIMESTAMP_RE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\]?")


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def read_frontmatter(path: Path) -> Tuple[Dict[str, str], int]:
    """Return (frontmatter, body_length_chars)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}, 0
    if not text.startswith("---\n"):
        return {}, len(text)
    end = text.find("\n---", 4)
    if end < 0:
        return {}, len(text)
    fm: Dict[str, str] = {}
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    body = text[end + 4:].lstrip("\n")
    return fm, len(body)


def count_callouts(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    return len(CALLOUT_RE.findall(text))


def find_concept_file(vault: Path, slug: str) -> Optional[Path]:
    """Search all 3 subfolders. Return first match."""
    concepts = vault / "0.Tags"
    candidates: List[Path] = []
    for sub in SUBFOLDERS:
        folder = concepts / sub
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            fm, _ = read_frontmatter(md)
            if fm.get("VW_concept_slug") == slug or slugify(md.stem) == slug:
                candidates.append(md)
    if not candidates:
        return None
    return candidates[0]


def load_index(index_path: Path) -> Dict[str, Dict]:
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    nodes = raw.get("nodes") or raw.get("concepts") or {}
    if isinstance(nodes, list):
        nodes = {n.get("slug", str(i)): n for i, n in enumerate(nodes)}
    return nodes


def find_inbound_wikilinks(vault: Path, slug: str, display_name: str,
                           cap: int = 20) -> List[Dict]:
    """Scan vault for wikilinks that resolve to this slug."""
    matches: List[Dict] = []
    name_lower = display_name.lower()
    for p in vault.rglob("*.md"):
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        # Skip concept files themselves
        if "0.Tags/" in str(p.relative_to(vault)).replace("\\", "/"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in WIKILINK_RE.finditer(line):
                target = m.group(1).strip()
                head = re.split(r"[#^]", target, maxsplit=1)[0].strip()
                basename = Path(head).name
                if slugify(basename) == slug or basename.lower() == name_lower:
                    matches.append({
                        "file": str(p.relative_to(vault)),
                        "line": i,
                        "context": line.strip()[:160],
                    })
                    if cap and len(matches) >= cap:
                        return matches
    return matches


def find_log_events(vault: Path, slug: str, display_name: str,
                    cap: int = 10) -> List[Dict]:
    log = vault / ".obsidian/plugins/vault-weaver/activity.log"
    if not log.is_file():
        return []
    events: List[Dict] = []
    needle_lower = display_name.lower()
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    for raw in lines:
        if slug not in raw and needle_lower not in raw.lower():
            continue
        ts_m = TIMESTAMP_RE.match(raw)
        events.append({
            "ts": ts_m.group(1) if ts_m else None,
            "line": raw.strip(),
        })
    # newest first; activity log is typically append-only chronological
    events.reverse()
    return events[:cap]


def diagnose(disk_info: Dict, index_node: Optional[Dict]) -> str:
    """Rule-based one-line diagnosis."""
    if not disk_info and not index_node:
        return "❌ unknown — no file on disk, no index entry."
    if not disk_info:
        return "⚠ index has entry but no file on disk — orphan index entry. Run /vault-weaver-health-check."
    if not index_node:
        return "⚠ file exists on disk but no index entry — orphan file. Run plugin's 'Reconcile index ↔ disk'."

    fm = disk_info["frontmatter"]
    sub = disk_info["subfolder"]
    idx_status = index_node.get("status", "pending")

    fm_rejected = fm.get("VW_rejected", "").lower() in ("true", "yes")
    fm_approved = fm.get("VW_approved", "").lower() in ("true", "yes")
    fm_status = "rejected" if fm_rejected else ("approved" if fm_approved else "pending")
    if fm.get("VW_status") in SUBFOLDERS:
        fm_status = fm["VW_status"]

    if sub == fm_status == idx_status:
        return f"✅ healthy — disk ({sub}), frontmatter ({fm_status}), and index ({idx_status}) all agree."
    if fm_status != sub:
        return (f"⚠ frontmatter says {fm_status} but file is in {sub}/ — "
                f"classic misplacement bug. Open plugin Maintenance → 'Reconcile from frontmatter'.")
    if idx_status != fm_status:
        return (f"⚠ index says {idx_status} but file/frontmatter say {fm_status} — "
                f"stale index. Run plugin's 'Reconcile index ↔ disk'.")
    return "⚠ inconsistent state — see fields above for details."


def render_human(slug: str, disk_info: Optional[Dict], node: Optional[Dict],
                 inbound: List[Dict], events: List[Dict], inbound_capped: bool) -> str:
    lines = []
    display = (node or {}).get("displayName") or (disk_info or {}).get("displayName") or slug
    lines.append(f"== Concept: {display} (slug: {slug}) ==\n")

    lines.append("Disk:")
    if disk_info:
        lines.append(f"  Path: {disk_info['rel_path']}")
        lines.append(f"  Subfolder: {disk_info['subfolder']}   (last-modified: {disk_info['mtime']})")
        lines.append("  Frontmatter:")
        for k in ("VW_status", "VW_approved", "VW_rejected", "VW_concept_slug", "VW_lang"):
            if k in disk_info["frontmatter"]:
                lines.append(f"    {k}: {disk_info['frontmatter'][k]}")
        lines.append(f"  Body: {disk_info['body_chars']} chars, {disk_info['callouts']} callouts")
    else:
        lines.append("  (no file found in 0.Tags/{approved,pending,rejected}/)")
    lines.append("")

    lines.append("Index:")
    if node:
        for k in ("status", "displayName", "summaryUpdatedAt"):
            if k in node:
                lines.append(f"  {k}: {node[k]}")
        pfs = node.get("perFileSummaries") or {}
        lines.append(f"  perFileSummaries: {len(pfs)} entries")
        for k in ("needsFullSynthesis", "signalScore", "duplicateOf", "duplicate_of", "blocked"):
            if k in node:
                lines.append(f"  {k}: {node[k]}")
    else:
        lines.append("  (no index entry)")
    lines.append("")

    extra = " (capped)" if inbound_capped else ""
    lines.append(f"Inbound wikilinks ({len(inbound)}{extra}):")
    if inbound:
        for m in inbound:
            lines.append(f"  {m['file']}:{m['line']}   \"{m['context']}\"")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"Timeline (last {len(events)} events):")
    if events:
        for e in events:
            ts = e.get("ts") or "—"
            lines.append(f"  {ts}  {e['line']}")
    else:
        lines.append("  (no activity log entries — log may be absent or this slug never moved)")
    lines.append("")

    lines.append(f"Diagnosis: {diagnose(disk_info or {}, node)}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--query", default=None,
                    help="Resolve query → list candidates (basename / displayName / partial)")
    ap.add_argument("--all", action="store_true",
                    help="Don't cap inbound wikilink list at 20")
    ap.add_argument("--format", choices=("human", "json"), default="human")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr); return 2

    if args.query and not args.slug:
        candidates = resolve_query(vault, args.query)
        if args.format == "json":
            print(json.dumps(candidates, indent=2))
        else:
            print(f"Candidates for query {args.query!r}: {len(candidates)}")
            for c in candidates[:20]:
                print(f"  {c['slug']:<40}  {c['rel_path']}")
            if len(candidates) > 20:
                print(f"  ... and {len(candidates) - 20} more")
        return 0 if candidates else 1

    if not args.slug:
        print("ERROR: --slug or --query required", file=sys.stderr); return 2

    slug = args.slug.strip()
    file = find_concept_file(vault, slug)
    disk_info: Optional[Dict] = None
    if file:
        fm, body_chars = read_frontmatter(file)
        try:
            mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc).isoformat()
        except Exception:
            mtime = "?"
        disk_info = {
            "rel_path": str(file.relative_to(vault)),
            "subfolder": file.parent.name,
            "frontmatter": fm,
            "body_chars": body_chars,
            "callouts": count_callouts(file),
            "mtime": mtime,
            "displayName": fm.get("VW_concept_slug") or file.stem,
        }

    index = load_index(vault / ".obsidian/plugins/vault-weaver/index.json")
    node = index.get(slug)
    display_name = (disk_info or {}).get("displayName") or (node or {}).get("displayName") or slug

    cap = 0 if args.all else 20
    inbound = find_inbound_wikilinks(vault, slug, display_name, cap=cap)
    inbound_capped = (not args.all) and len(inbound) >= 20

    events = find_log_events(vault, slug, display_name, cap=10)

    if args.format == "json":
        out = {
            "slug": slug, "disk": disk_info, "index": node,
            "inbound": inbound, "timeline": events,
            "diagnosis": diagnose(disk_info or {}, node),
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        print(render_human(slug, disk_info, node, inbound, events, inbound_capped))

    return 0


def resolve_query(vault: Path, query: str) -> List[Dict]:
    q = query.lower().strip()
    q_slug = slugify(q)
    out: List[Dict] = []
    concepts = vault / "0.Tags"
    seen: set = set()
    for sub in SUBFOLDERS:
        folder = concepts / sub
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            fm, _ = read_frontmatter(md)
            slug = fm.get("VW_concept_slug") or slugify(md.stem)
            if slug in seen:
                continue
            name = md.stem
            if (q == slug or q_slug == slug or q in name.lower()
                    or q in slug or q_slug in slug):
                seen.add(slug)
                out.append({
                    "slug": slug,
                    "rel_path": str(md.relative_to(vault)),
                    "displayName": name,
                })
    return out


if __name__ == "__main__":
    sys.exit(main())
