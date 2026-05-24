#!/usr/bin/env python3
"""
Scan an Obsidian vault and summarize core/community plugin capabilities.

Usage:
  scan_obsidian_capabilities.py --vault /path/to/vault --format markdown
  scan_obsidian_capabilities.py --vault /path/to/vault --format json --out capabilities.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CAPABILITY_RULES = {
    "dataview": ["query-blocks", "inline-dataview", "computed-metadata"],
    "periodic-notes": ["periodic-note-pathing", "date-based-note-lifecycle"],
    "tag-wrangler": ["tag-refactor", "tag-rename-workflows"],
    "text-extractor": ["extracted-text-sidecar", "attachment-text-search-indexing"],
    "obsidian-spaced-repetition": ["spaced-repetition-markers", "flashcard-syntax"],
    "smart-connections": ["ai-linking-metadata", "semantic-indexing-side-effects"],
    "obsidian-zotero-desktop-connector": ["zotero-citation-blocks", "reference-import-templates"],
    "pdf-plus": ["pdf-annotation-links", "pdf-workflow-extensions"],
    "daily-note-calendar": ["daily-note-navigation", "date-note-conventions"],
}

KEYWORD_RULES = {
    "query": "query-blocks",
    "calendar": "calendar/date-automation",
    "template": "template-driven-content",
    "tag": "tag-taxonomy-management",
    "task": "task-tracking-syntax",
    "citation": "citation-workflows",
    "zotero": "citation-workflows",
    "pdf": "pdf-workflows",
    "ai": "ai-assisted-content",
    "export": "export-pipeline-effects",
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def infer_capabilities(plugin_id: str, manifest: dict[str, Any]) -> list[str]:
    caps: set[str] = set(CAPABILITY_RULES.get(plugin_id, []))

    text = " ".join(
        [
            str(manifest.get("name", "")),
            str(manifest.get("description", "")),
            plugin_id,
        ]
    ).lower()
    tokens = set(re.findall(r"[a-z0-9]+", text))

    for keyword, capability in KEYWORD_RULES.items():
        # Single-token keywords should match token boundaries (for example, "ai"
        # should not match inside "daily"). Multi-token keywords can use phrase matching.
        if " " in keyword:
            matched = keyword in text
        else:
            matched = keyword in tokens
        if matched:
            caps.add(capability)

    if not caps:
        caps.add("general-content-extension")

    return sorted(caps)


def scan_vault(vault: Path) -> dict[str, Any]:
    obsidian = vault / ".obsidian"
    plugin_root = obsidian / "plugins"

    enabled_core = read_json(obsidian / "core-plugins.json", [])
    enabled_community = read_json(obsidian / "community-plugins.json", [])

    installed_dirs = sorted(
        [p for p in plugin_root.iterdir() if p.is_dir()]
    ) if plugin_root.exists() else []

    plugins: list[dict[str, Any]] = []
    for pdir in installed_dirs:
        pid = pdir.name
        manifest_path = pdir / "manifest.json"
        data_path = pdir / "data.json"

        manifest = read_json(manifest_path, {})
        configured = data_path.exists()

        plugins.append(
            {
                "id": pid,
                "enabled": pid in enabled_community,
                "configured": configured,
                "version": manifest.get("version"),
                "name": manifest.get("name"),
                "description": manifest.get("description"),
                "minAppVersion": manifest.get("minAppVersion"),
                "capabilities": infer_capabilities(pid, manifest),
            }
        )

    return {
        "vault": str(vault),
        "obsidian_config_exists": obsidian.exists(),
        "core_plugins_enabled": sorted(enabled_core),
        "community_plugins_enabled": sorted(enabled_community),
        "community_plugins_installed": plugins,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Obsidian Vault Capability Scan")
    lines.append("")
    lines.append(f"- Vault: `{report['vault']}`")
    lines.append(f"- `.obsidian` detected: `{report['obsidian_config_exists']}`")
    lines.append(f"- Core plugins enabled: `{len(report['core_plugins_enabled'])}`")
    lines.append(f"- Community plugins enabled: `{len(report['community_plugins_enabled'])}`")
    lines.append(f"- Community plugins installed: `{len(report['community_plugins_installed'])}`")
    lines.append("")

    lines.append("## Enabled Core Plugins")
    lines.append("")
    if report["core_plugins_enabled"]:
        for pid in report["core_plugins_enabled"]:
            lines.append(f"- `{pid}`")
    else:
        lines.append("- None detected")
    lines.append("")

    lines.append("## Community Plugins")
    lines.append("")
    lines.append("| id | enabled | configured | version | inferred capabilities |")
    lines.append("| --- | --- | --- | --- | --- |")

    for plugin in report["community_plugins_installed"]:
        caps = ", ".join(plugin["capabilities"])
        lines.append(
            f"| `{plugin['id']}` | `{plugin['enabled']}` | `{plugin['configured']}` | `{plugin.get('version')}` | {caps} |"
        )

    if not report["community_plugins_installed"]:
        lines.append("| _(none)_ | - | - | - | - |")

    lines.append("")
    lines.append("## Operational Notes")
    lines.append("")
    lines.append("- Treat plugin-specific syntax as protected unless task explicitly asks to rewrite it.")
    lines.append("- Prioritize plugin-enabled workflows when proposing automation or metadata refactors.")
    lines.append("- Re-run this scan after major vault/plugin changes before batch edits.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Obsidian plugin capabilities for a vault")
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", help="Write output to file instead of stdout")
    args = parser.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists() or not vault.is_dir():
        raise SystemExit(f"Vault path is invalid: {vault}")

    report = scan_vault(vault)
    output = to_markdown(report) if args.format == "markdown" else json.dumps(report, indent=2)

    if args.out:
        Path(args.out).expanduser().resolve().write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
