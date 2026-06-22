#!/usr/bin/env python3
"""Regenerate the ## Skills table in README.md from each */SKILL.md frontmatter.

Keeps the public README index from going stale. Writes the table between
<!-- skills:start --> / <!-- skills:end --> markers, inserting/replacing the
## Skills section if the markers aren't present yet. Idempotent.
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.claude/skills")
README = os.path.join(ROOT, "README.md")
START, END = "<!-- skills:start -->", "<!-- skills:end -->"


def parse(skill_md, fallback):
    with open(skill_md, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
    fm = m.group(1) if m else ""
    nm = re.search(r"^name:\s*(.+)$", fm, re.M)
    dm = re.search(r"^description:\s*(.+)$", fm, re.M)
    name = nm.group(1).strip().strip("\"'") if nm else fallback
    desc = dm.group(1).strip().strip("\"'") if dm else ""
    first = re.split(r"(?<=[.])\s", desc)[0] if desc else ""
    if len(first) > 100:
        first = first[:97].rstrip() + "..."
    first = first.replace("|", "\\|")
    return name, first


rows = []
for d in sorted(os.listdir(ROOT)):
    sm = os.path.join(ROOT, d, "SKILL.md")
    if os.path.isfile(sm):
        rows.append(parse(sm, d))

table = "| Skill | Description |\n|---|---|\n" + "\n".join(
    f"| `{n}` | {desc} |" for n, desc in rows
)
block = f"{START}\n\n{table}\n\n{END}"

with open(README, encoding="utf-8") as fh:
    content = fh.read()

new_section = f"## Skills\n\n{block}\n"
if START in content and END in content:
    content = re.sub(
        re.escape(START) + r".*?" + re.escape(END), lambda _: block, content, flags=re.S
    )
else:
    # Replace only the existing "## Skills" section, up to the next H2 or EOF, so
    # sibling sections (e.g. ## Compatibility) that follow it are preserved.
    m = re.search(r"^## Skills[ \t]*\n.*?(?=^## |\Z)", content, flags=re.S | re.M)
    if m:
        content = content[: m.start()] + new_section + "\n" + content[m.end() :]
    else:
        content = content.rstrip() + f"\n\n{new_section}"

with open(README, "w", encoding="utf-8") as fh:
    fh.write(content)

print(f"README updated: {len(rows)} skills indexed.")
