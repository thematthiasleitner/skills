#!/usr/bin/env python3
"""Vault-wide Obsidian wikilink scanner / rewriter — dry-run-by-default.

Usage:
    wikilink_scanner.py --vault PATH --op OPERATION [...flags...] [--dry-run|--apply]

Operations:
    find-orphans     List [[X]] whose target file does not exist anywhere in vault.
    find-broken      Like find-orphans but restricted to --scope glob.
    strip-prefix     Rewrite [[<prefix>X]] → [[X]]. Requires --prefix.
    strip-slugs      Remove [[X|...]] where slug X is in --slugs-file (one per line).

Flags:
    --scope GLOB       Limit to files matching glob (e.g. "0.Tags/**/*.md")
    --prefix STR       For strip-prefix
    --slugs-file PATH  For strip-slugs (one slug per line, # comments allowed)
    --dry-run          Default. Prints planned edits.
    --apply            Required to mutate files.
    --sample N         How many sample edits to print in dry-run (default 10).
    --format human|json

Atomic writes: writes to path.md.tmp then os.replace().
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

WIKILINK_RE = re.compile(r"\[\[([^\[\]\|]+?)(\|[^\[\]]+?)?\]\]")


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


def iter_md(vault: Path, scope_glob: str | None) -> Iterable[Path]:
    if scope_glob:
        yield from vault.glob(scope_glob)
    else:
        for p in vault.rglob("*.md"):
            # Skip dotfolders (.obsidian, .git, .trash)
            if any(part.startswith(".") for part in p.relative_to(vault).parts):
                continue
            yield p


def build_existing_targets(vault: Path) -> Set[str]:
    """Set of basenames (without .md) AND vault-relative paths (without .md)
    that wikilinks could legitimately resolve to."""
    out: Set[str] = set()
    for p in vault.rglob("*.md"):
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        out.add(p.stem)
        rel = str(p.relative_to(vault).with_suffix(""))
        out.add(rel)
    return out


def op_find_orphans(vault: Path, scope: str | None) -> List[Dict]:
    targets = build_existing_targets(vault)
    out: List[Dict] = []
    for path in iter_md(vault, scope):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            # Strip Obsidian section anchor (#) and block ref (^)
            head = re.split(r"[#^]", target, maxsplit=1)[0].strip()
            if not head:
                continue
            if head in targets:
                continue
            # Also try basename of path-like target
            if Path(head).name in targets:
                continue
            out.append({
                "file": str(path.relative_to(vault)),
                "wikilink": m.group(0),
                "target": head,
            })
    return out


def op_strip_prefix(vault: Path, scope: str | None, prefix: str) -> List[Dict]:
    """Find [[<prefix>X]] occurrences. Returns planned edits."""
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    out: List[Dict] = []
    for path in iter_md(vault, scope):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        edits: List[Tuple[str, str]] = []
        def repl(m: re.Match) -> str:
            target = m.group(1)
            alias = m.group(2) or ""
            if target.startswith(prefix):
                new_target = target[len(prefix):]
                new = f"[[{new_target}{alias}]]"
                edits.append((m.group(0), new))
                return new
            return m.group(0)
        new_text = WIKILINK_RE.sub(repl, text)
        if edits:
            out.append({
                "file": str(path.relative_to(vault)),
                "old_text": text,
                "new_text": new_text,
                "edits": edits,
            })
    return out


def op_strip_slugs(vault: Path, scope: str | None, slugs: Set[str]) -> List[Dict]:
    """Remove [[X]] (and [[X|alias]]) where slugify(target-basename) is in slugs."""
    out: List[Dict] = []
    for path in iter_md(vault, scope):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        edits: List[Tuple[str, str]] = []
        def repl(m: re.Match) -> str:
            target = m.group(1).strip()
            head = re.split(r"[#^]", target, maxsplit=1)[0].strip()
            basename = Path(head).name
            slug = slugify(basename)
            if slug in slugs:
                # Replace with just the alias text if present, else the basename.
                alias = m.group(2) or ""
                replacement = alias[1:] if alias else basename
                edits.append((m.group(0), replacement))
                return replacement
            return m.group(0)
        new_text = WIKILINK_RE.sub(repl, text)
        if edits:
            out.append({
                "file": str(path.relative_to(vault)),
                "old_text": text,
                "new_text": new_text,
                "edits": edits,
            })
    return out


def apply_edits(planned: List[Dict]) -> int:
    """Atomic write: tmp + rename. Returns count of files actually written."""
    written = 0
    for entry in planned:
        # find-orphans entries have no new_text — skip
        if "new_text" not in entry:
            continue
        path = Path(entry["file"])  # caller is responsible for cwd OR absolute
        if not path.is_absolute():
            # Caller passed vault-relative — we don't have vault here, so the
            # caller wraps absolute paths into the planned list before this.
            continue
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(entry["new_text"], encoding="utf-8")
        os.replace(tmp, path)
        written += 1
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--op", required=True,
                    choices=("find-orphans", "find-broken", "strip-prefix", "strip-slugs"))
    ap.add_argument("--scope", default=None)
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--slugs-file", default=None)
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", action="store_true", default=True)
    grp.add_argument("--apply", action="store_true", default=False)
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--format", choices=("human", "json"), default="human")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr)
        return 2

    # Op execution
    if args.op in ("find-orphans", "find-broken"):
        scope = args.scope if args.op == "find-broken" else None
        results = op_find_orphans(vault, scope)
        render_finds(results, args)
        return 1 if results else 0

    if args.op == "strip-prefix":
        if not args.prefix:
            print("ERROR: --prefix required", file=sys.stderr); return 2
        planned = op_strip_prefix(vault, args.scope, args.prefix)
    elif args.op == "strip-slugs":
        if not args.slugs_file:
            print("ERROR: --slugs-file required", file=sys.stderr); return 2
        slugs = load_slugs(Path(args.slugs_file))
        planned = op_strip_slugs(vault, args.scope, slugs)
    else:
        print(f"unknown op: {args.op}", file=sys.stderr); return 2

    # Make paths absolute for safe apply
    for entry in planned:
        entry["_abs_path"] = str(vault / entry["file"])

    render_planned(planned, args)

    if args.apply and planned:
        # Apply
        written = 0
        for entry in planned:
            path = Path(entry["_abs_path"])
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(entry["new_text"], encoding="utf-8")
            os.replace(tmp, path)
            written += 1
        print(f"\n=== APPLIED to {written} files ===")
    elif not args.apply:
        print("\n(dry-run; pass --apply to write changes)")

    return 1 if planned else 0


def render_finds(results: List[Dict], args) -> None:
    if args.format == "json":
        print(json.dumps(results, indent=2)); return
    print(f"=== {args.op} ===")
    print(f"Scope: {args.scope or 'vault-wide'}")
    print(f"Found {len(results)} link(s)")
    for r in results[:args.sample]:
        print(f"  {r['file']}  →  {r['wikilink']}")
    if len(results) > args.sample:
        print(f"  ... and {len(results) - args.sample} more")


def render_planned(planned: List[Dict], args) -> None:
    if args.format == "json":
        compact = [{
            "file": p["file"],
            "edit_count": len(p["edits"]),
            "edits_sample": [{"old": o, "new": n} for o, n in p["edits"][:3]],
        } for p in planned]
        print(json.dumps(compact, indent=2)); return
    total_edits = sum(len(p["edits"]) for p in planned)
    label = "=== APPLY ===" if args.apply else "=== DRY RUN ==="
    print(label)
    print(f"Op: {args.op}")
    print(f"Scope: {args.scope or 'vault-wide'}")
    print(f"Files to modify: {len(planned)}  Total wikilink edits: {total_edits}")
    print()
    print(f"Sample edits (first {args.sample}):")
    shown = 0
    for entry in planned:
        for old, new in entry["edits"]:
            if shown >= args.sample:
                break
            print(f"  {entry['file']}  {old}  →  {new}")
            shown += 1
        if shown >= args.sample:
            break
    if total_edits > args.sample:
        print(f"  ... and {total_edits - args.sample} more")


def load_slugs(path: Path) -> Set[str]:
    out: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
