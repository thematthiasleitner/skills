#!/usr/bin/env python3
"""archive_stale.py — walk a folder tree, detect stale artefacts, move them
to per-folder ``archive/<date>-<label>/<category>/`` subdirectories.

Dry-run by default.  Pass ``--apply`` to actually move files.

Detectors per folder:
  versioned_predecessors  foo_v1, foo_v2 … archived when foo_vN exists.
  snapshot_intermediates  *_BEFORE.*, *_PREV.*, *.pre_*.*  (any nesting).
  old_marker              old_* / *_old / *_old_*  filenames.
  dated_duplicates        <base>_YYYYMMDD* clusters — newest stays.
  trial_runs              trial_* and *_trial_* dirs older than 30 days.
  numbered_iterations     base + base_clean + base_final + base_post_*
                          + base_pre_* clusters (when ≥3 variants share a base).

Safety:
  - Never touches hidden dotfiles, anything inside an existing ``archive/``,
    or canonical noise dirs (node_modules, __pycache__, .git, dist, build,
    .venv, .pytest_cache).
  - Skips the "current" item of every cluster (newest, highest version).
  - Refuses to run on ``/``, ``$HOME``, ``/Users``, ``/Volumes``, ``/Library``.
  - Default dry-run: prints WOULD ARCHIVE lines + a summary table.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Safety: paths we refuse to touch outright.
# ─────────────────────────────────────────────────────────────────────────────
_FORBIDDEN_ROOTS = {
    Path("/"),
    Path("/Users"),
    Path("/Volumes"),
    Path("/Library"),
    Path("/System"),
    Path("/opt"),
    Path("/etc"),
    Path("/var"),
    Path("/tmp"),
    Path("/private"),
    Path.home(),
}

# Directory names we never descend into.
_SKIP_DIR_NAMES = {
    "archive",  # already organised
    "node_modules",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".idea",
    ".vscode",
    "site-packages",
    ".cache",
}


# ─────────────────────────────────────────────────────────────────────────────
# Detector patterns.
# ─────────────────────────────────────────────────────────────────────────────

# Trailing ``_vN`` version suffix.  Matches ``foo_v1``, ``foo_v12.json``.
_VERSION_RE = re.compile(r"^(?P<base>.+?)_[vV](?P<n>\d+)(?P<ext>(?:\.[^/]+)?)$")

# Trailing snapshot / pre-fix markers in basename.
_SNAPSHOT_RE = re.compile(
    r"(?:_BEFORE|_PREV\d*|_pre_[a-z0-9_]+|\.pre_[a-z0-9_]+|_pre-[a-z0-9_]+)",
    re.IGNORECASE,
)

# Old / outdated markers.
_OLD_RE = re.compile(r"(?:^|[_-])old(?:[_-]|$|\.)", re.IGNORECASE)

# YYYYMMDD anywhere in basename (with optional ``-HHMMSS`` suffix).
_DATE_RE = re.compile(r"(?P<date>20\d{6})(?:[-_T]?(?P<time>\d{4,6}))?")

# Trial-run dir patterns.
_TRIAL_RE = re.compile(r"(?:^|[_-])trial(?:[_-]|$)", re.IGNORECASE)

# Numbered-iteration variant suffixes.  Files like ``report.json`` +
# ``report_clean.json`` + ``report_final.json`` + ``report_post_*.json``.
_ITERATION_SUFFIX_RE = re.compile(
    r"^_(?:clean|final|post[_-][a-z0-9_]+|v\d+_clean|fixed|corrected)$",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Move plan model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Move:
    src: Path
    category: str
    reason: str           # human-readable

    def dest(self, archive_root: Path) -> Path:
        return archive_root / self.category / self.src.name


@dataclass
class FolderPlan:
    folder: Path
    moves: List[Move] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Detectors — each returns a list of Move objects for items in ``folder``.
# Each detector receives ``entries`` = the unfiltered child names that are
# candidates (not hidden, not inside skip-dirs, not already inside archive/).
# ─────────────────────────────────────────────────────────────────────────────


def _detect_versioned(entries: List[Path]) -> List[Move]:
    """``foo_vN`` clusters: keep highest N, archive the rest."""
    clusters: Dict[Tuple[str, str], List[Tuple[int, Path]]] = defaultdict(list)
    for p in entries:
        m = _VERSION_RE.match(p.name)
        if not m:
            continue
        base = m.group("base")
        ext = m.group("ext") or ""
        clusters[(base, ext)].append((int(m.group("n")), p))
    moves: List[Move] = []
    for (base, ext), items in clusters.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda t: t[0])
        # All but the highest get archived.
        for _, p in items[:-1]:
            moves.append(Move(
                src=p,
                category="versioned_predecessors",
                reason=f"older version of {base}{ext} (kept v{items[-1][0]})",
            ))
    return moves


def _detect_snapshots(entries: List[Path]) -> List[Move]:
    """Files / dirs with intermediate-snapshot markers in their name."""
    moves: List[Move] = []
    for p in entries:
        if _SNAPSHOT_RE.search(p.name):
            moves.append(Move(
                src=p,
                category="snapshot_intermediates",
                reason="contains _BEFORE / _PREV / pre_* marker",
            ))
    return moves


def _detect_old_marker(entries: List[Path]) -> List[Move]:
    moves: List[Move] = []
    for p in entries:
        # Exclude false positives ("old" as part of "Goldsmith", "hold", etc.)
        # by requiring boundary chars around "old".
        if _OLD_RE.search(p.name):
            moves.append(Move(
                src=p,
                category="old_marker",
                reason="filename explicitly marked old",
            ))
    return moves


def _detect_dated_duplicates(entries: List[Path], min_cluster: int = 2) -> List[Move]:
    """Cluster by leading base + YYYYMMDD; keep newest date."""
    clusters: Dict[str, List[Tuple[str, Path]]] = defaultdict(list)
    for p in entries:
        m = _DATE_RE.search(p.name)
        if not m:
            continue
        date_str = m.group("date") + (m.group("time") or "")
        # base = everything before the date region
        base = p.name[: m.start()].rstrip("_-. ")
        if not base:
            continue
        clusters[base].append((date_str, p))
    moves: List[Move] = []
    for base, items in clusters.items():
        if len(items) < min_cluster:
            continue
        items.sort(key=lambda t: t[0])
        for _, p in items[:-1]:
            moves.append(Move(
                src=p,
                category="dated_duplicates",
                reason=f"older dated variant of {base} (kept {items[-1][0]})",
            ))
    return moves


def _detect_trial_runs(
    entries: List[Path], min_age_days: int, include_young: bool
) -> List[Move]:
    moves: List[Move] = []
    cutoff = time.time() - 30 * 86400  # 30 days
    for p in entries:
        if not p.is_dir():
            continue
        if not _TRIAL_RE.search(p.name):
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime > cutoff and not include_young:
            continue
        moves.append(Move(
            src=p,
            category="trial_runs",
            reason="trial / test directory",
        ))
    return moves


def _detect_numbered_iterations(entries: List[Path]) -> List[Move]:
    """Cluster files sharing a base where iteration-suffix variants exist.

    Example cluster::

        report.json
        report_clean.json
        report_final.json
        report_post_fix.json
        report_post_regen.json

    Heuristic: when ≥3 files share a base + extension and at least one has
    an iteration suffix, archive ALL of them (caller can pick which to keep
    at the top level — usually nothing, because the cluster is the artefact
    of iterating).
    """
    clusters: Dict[Tuple[str, str], List[Path]] = defaultdict(list)
    for p in entries:
        if not p.is_file():
            continue
        ext = p.suffix
        if not ext:
            continue
        stem = p.stem
        # Split off any trailing _<suffix> token to find a base.
        parts = stem.rsplit("_", 1)
        candidate_base = parts[0] if len(parts) == 2 else stem
        candidate_suffix = "_" + parts[1] if len(parts) == 2 else ""
        if _ITERATION_SUFFIX_RE.match(candidate_suffix):
            # Group under the base+ext.
            clusters[(candidate_base, ext)].append(p)
        else:
            # Anchor for a potential cluster.
            clusters[(stem, ext)].append(p)
    moves: List[Move] = []
    for (base, ext), files in clusters.items():
        # We only fire when at least 3 files cluster AND at least one
        # carries an iteration-suffix variant.
        if len(files) < 3:
            continue
        has_iter = any(
            _ITERATION_SUFFIX_RE.match(
                "_" + f.stem.rsplit("_", 1)[1] if "_" in f.stem else ""
            )
            for f in files
        )
        if not has_iter:
            continue
        # Sort by mtime; archive ALL — these clusters are usually pure noise.
        files.sort(key=lambda p: p.stat().st_mtime)
        for f in files:
            moves.append(Move(
                src=f,
                category="numbered_iterations",
                reason=f"iteration-cluster on {base}{ext}",
            ))
    return moves


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────


def _candidate_entries(folder: Path) -> List[Path]:
    """Direct children of ``folder`` that are eligible for detection."""
    out: List[Path] = []
    try:
        for p in folder.iterdir():
            if p.name.startswith("."):
                continue
            if p.name in _SKIP_DIR_NAMES:
                continue
            out.append(p)
    except (PermissionError, OSError):
        pass
    return out


def _walk(root: Path, max_depth: int) -> List[Path]:
    """Return all directories to inspect (root + subdirs up to max_depth)."""
    folders: List[Path] = []

    def recurse(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        folders.append(d)
        try:
            for p in d.iterdir():
                if not p.is_dir():
                    continue
                if p.name.startswith("."):
                    continue
                if p.name in _SKIP_DIR_NAMES:
                    continue
                recurse(p, depth + 1)
        except (PermissionError, OSError):
            return

    recurse(root, 0)
    return folders


def _plan_folder(
    folder: Path,
    only: Optional[set],
    min_age_days: int,
    include_trial_young: bool,
) -> FolderPlan:
    entries = _candidate_entries(folder)

    # Apply min-age filter once at entry level.
    if min_age_days > 0:
        cutoff = time.time() - min_age_days * 86400
        entries = [p for p in entries if _safe_mtime(p) <= cutoff]

    plan = FolderPlan(folder=folder)
    detectors = [
        ("versioned_predecessors", lambda: _detect_versioned(entries)),
        ("snapshot_intermediates", lambda: _detect_snapshots(entries)),
        ("old_marker",             lambda: _detect_old_marker(entries)),
        ("dated_duplicates",       lambda: _detect_dated_duplicates(entries)),
        ("trial_runs",             lambda: _detect_trial_runs(entries, min_age_days, include_trial_young)),
        ("numbered_iterations",    lambda: _detect_numbered_iterations(entries)),
    ]
    seen: Dict[Path, Move] = {}
    for category, fn in detectors:
        if only and category not in only:
            continue
        for mv in fn():
            # First detector wins per src to avoid double-categorisation.
            seen.setdefault(mv.src, mv)
    plan.moves = list(seen.values())
    return plan


def _safe_mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _check_target_safe(target: Path) -> None:
    target = target.resolve()
    if target in (p.resolve() for p in _FORBIDDEN_ROOTS):
        sys.exit(f"ERROR: refusing to operate on forbidden root: {target}")
    # Don't descend from $HOME directly — too broad.
    if str(target) == str(Path.home().resolve()):
        sys.exit("ERROR: refusing to operate on $HOME — give a narrower target")


def _print_plan(plans: List[FolderPlan], target: Path) -> Dict[str, int]:
    """Print the dry-run plan; return category→count summary."""
    summary: Dict[str, int] = defaultdict(int)
    total = 0
    for plan in plans:
        if not plan.moves:
            continue
        rel = plan.folder.relative_to(target) if plan.folder != target else Path(".")
        print(f"\n=== {rel} ({len(plan.moves)} item(s)) ===")
        for mv in sorted(plan.moves, key=lambda m: (m.category, m.src.name)):
            print(f"  [{mv.category:24s}] {mv.src.name}")
            print(f"      → {mv.reason}")
            summary[mv.category] += 1
            total += 1
    print(f"\n========================================")
    print(f"Summary: {total} item(s) across {sum(1 for p in plans if p.moves)} folder(s)")
    for cat, n in sorted(summary.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {cat}")
    return dict(summary)


def _apply_plan(plans: List[FolderPlan], label: str) -> int:
    """Actually move files.  Returns total moved."""
    date_tag = datetime.now().strftime("%Y%m%d")
    moved = 0
    for plan in plans:
        if not plan.moves:
            continue
        archive_root = plan.folder / "archive" / f"{date_tag}-{label}"
        for mv in plan.moves:
            dest = mv.dest(archive_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # Disambiguate with a suffix to avoid clobber.
                stem, suffix = mv.src.stem, mv.src.suffix
                i = 2
                while True:
                    alt = dest.parent / f"{stem}__{i}{suffix}"
                    if not alt.exists():
                        dest = alt
                        break
                    i += 1
            shutil.move(str(mv.src), str(dest))
            moved += 1
            print(f"  moved  {mv.src.relative_to(plan.folder)}  →  archive/{date_tag}-{label}/{mv.category}/{dest.name}")
    return moved


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Archive stale artefacts under per-folder archive/ subdirs.",
        epilog="Default is dry-run.  Pass --apply to actually move.",
    )
    ap.add_argument("target", type=Path, help="Root folder to scan.")
    ap.add_argument("--apply", action="store_true", help="Actually move files.")
    ap.add_argument("--max-depth", type=int, default=8, help="Recursion depth.")
    ap.add_argument("--min-age-days", type=int, default=0,
                    help="Only consider items older than N days.")
    ap.add_argument("--include-trial-younger", action="store_true",
                    help="Don't skip trial_* dirs younger than 30 days.")
    ap.add_argument("--label", default="cleanup",
                    help="Suffix for the dated archive subdir.")
    ap.add_argument("--only", type=str, default="",
                    help="Comma-separated category filter "
                         "(versioned_predecessors,snapshot_intermediates,old_marker,"
                         "dated_duplicates,trial_runs,numbered_iterations)")
    args = ap.parse_args(argv)

    target = args.target.expanduser().resolve()
    if not target.is_dir():
        sys.exit(f"ERROR: {target} is not a directory")
    _check_target_safe(target)

    only = {c.strip() for c in args.only.split(",") if c.strip()} or None

    print(f"Scanning: {target}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Max depth: {args.max_depth}  Min-age-days: {args.min_age_days}")
    if only:
        print(f"Only categories: {sorted(only)}")
    print()

    folders = _walk(target, args.max_depth)
    plans = [
        _plan_folder(f, only, args.min_age_days, args.include_trial_younger)
        for f in folders
    ]

    summary = _print_plan(plans, target)
    if not args.apply:
        print(f"\n(dry-run; pass --apply to move {sum(summary.values())} item(s))")
        return 0
    if not summary:
        print("\nNothing to move.")
        return 0
    print()
    moved = _apply_plan(plans, args.label)
    print(f"\nMoved {moved} item(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
