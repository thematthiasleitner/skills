#!/usr/bin/env python3
"""Update Obsidian plugin version metadata in manifest.json and versions.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update manifest.json and versions.json for an Obsidian plugin release."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to manifest.json",
    )
    parser.add_argument(
        "--versions",
        type=Path,
        required=True,
        help="Path to versions.json",
    )
    parser.add_argument(
        "--version",
        type=str,
        required=True,
        help="Plugin version to set (example: 1.2.0)",
    )
    parser.add_argument(
        "--min-app-version",
        type=str,
        help="Optional minimum Obsidian app version to set in manifest and versions map",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}, got {type(data).__name__}")
    return data


def parse_semver_core(version: str) -> Tuple[int, ...] | None:
    core = version.split("-", maxsplit=1)[0]
    parts = core.split(".")
    values = []
    for part in parts:
        if not part.isdigit():
            return None
        values.append(int(part))
    return tuple(values)


def ordered_versions(versions: Dict[str, str]) -> Dict[str, str]:
    def sort_key(item: Tuple[str, str]) -> Tuple[int, Tuple[int, ...], str]:
        version = item[0]
        parsed = parse_semver_core(version)
        if parsed is None:
            return (1, (0,), version)
        return (0, parsed, version)

    items = sorted(versions.items(), key=sort_key)
    return {version: min_app for version, min_app in items}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def main() -> None:
    args = parse_args()

    manifest = load_json(args.manifest)
    versions = load_json(args.versions)

    if "minAppVersion" not in manifest:
        raise KeyError(f"'minAppVersion' is missing in {args.manifest}")

    manifest["version"] = args.version
    if args.min_app_version:
        manifest["minAppVersion"] = args.min_app_version

    min_app_version = str(manifest["minAppVersion"])
    versions[str(args.version)] = min_app_version
    versions = ordered_versions(versions)

    write_json(args.manifest, manifest)
    write_json(args.versions, versions)

    print(f"Updated {args.manifest} version -> {manifest['version']}")
    print(f"Updated {args.manifest} minAppVersion -> {manifest['minAppVersion']}")
    print(f"Updated {args.versions} entry -> {args.version}: {min_app_version}")


if __name__ == "__main__":
    main()
