#!/usr/bin/env python3
"""
reference-flashcards / scan.py

Deterministic planner for the reference-flashcards skill.

For every article PDF in Thesis/References (the curated thesis reference set),
decide what the Obsidian vault needs:

  - create   : no note for this article in the ACTIVE vault References tree
  - add_cards: a note exists but has no flashcards yet
  - skip     : a note exists and already has flashcards

"Already in the vault" is scoped to the ACTIVE References tree only. The
`archive/` subtree is treated as an untouched backup and is IGNORED here, so
the planner never reports an archived note as "already present".

Outputs JSON to stdout. Zero tokens, no LLM.

Usage:
  python3 scan.py                          # full plan over all present PDFs
  python3 scan.py --article aitken         # filter by author/year/filename substring
  python3 scan.py --thesis-refs PATH --vault-refs PATH
"""
import argparse
import json
import os
import re
import sys
import unicodedata

# --- Defaults (this workspace) ------------------------------------------------
HOME = os.path.expanduser("~")
DEFAULT_THESIS_REFS = os.path.join(
    HOME,
    "Library/CloudStorage/OneDrive-UniversitédeGenève/RA NEAD/Thesis/References",
)
DEFAULT_VAULT_REFS = os.path.join(
    HOME, "ObsVault/1.Projects/RA MSc NEAD/References"
)

# Folders never scanned for "already present" notes, and never scanned for PDFs.
SKIP_DIRS = {"archive", "_needs_replacement", ".archive", ".obsidian", ".trash"}

# Flashcard signals (Obsidian Spaced Repetition plugin).
SR_COMMENT = re.compile(r"<!--SR:")
ML_SEP = re.compile(r"^\s*\?{1,2}\s*$")           # `?` or `??` on its own line
# single-line `::` / `:::` that is NOT inside a wikilink [[a::b]] or a URL/code
SL_SEP = re.compile(r"(?<!\[)(?<!:):{2,3}(?!:)(?!\])")


def deaccent(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def first_author(authors: str) -> str:
    """Reduce an author string from a filename to a normalized first-author key."""
    a = authors.strip()
    # cut at the first author-list delimiter
    for delim in [" et al", ", ", " and ", " & ", ","]:
        idx = a.lower().find(delim.lower()) if delim != "," else a.find(",")
        if idx != -1:
            a = a[:idx]
            break
    a = deaccent(a).lower()
    a = re.sub(r"[^a-z]", "", a)
    return a


def parse_pdf_name(fname: str):
    """Return (author_key, display_author, year) from a reference PDF filename."""
    stem = re.sub(r"\.pdf$", "", fname, flags=re.IGNORECASE)
    year_m = re.search(r"(19|20)\d{2}", stem)
    year = year_m.group(0) if year_m else "0000"
    # authors are everything before the first ' - ' or the year
    if " - " in stem:
        authors = stem.split(" - ", 1)[0]
    else:
        authors = stem[: year_m.start()] if year_m else stem
    authors = authors.rstrip(" ,").strip()
    display = authors if authors else stem
    return first_author(authors), display, year


def has_flashcards(text: str) -> int:
    """Count flashcard signals in a note (>0 means cards exist)."""
    n = 0
    for line in text.splitlines():
        if SR_COMMENT.search(line):
            n += 1
        elif ML_SEP.match(line):
            n += 1
        elif SL_SEP.search(line) and "[[" not in line and "http" not in line:
            n += 1
    return n


def index_active_notes(vault_refs: str):
    """Map first-author+year key -> note path, for the ACTIVE tree only."""
    idx = {}
    for root, dirs, files in os.walk(vault_refs):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.lower().endswith(".md"):
                continue
            key_author, _, year = parse_pdf_name(f)  # same parser works on note names
            if key_author and year != "0000":
                idx[f"{key_author}_{year}"] = os.path.join(root, f)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thesis-refs", default=DEFAULT_THESIS_REFS)
    ap.add_argument("--vault-refs", default=DEFAULT_VAULT_REFS)
    ap.add_argument("--article", default=None,
                    help="substring filter on PDF filename (author/year/title)")
    args = ap.parse_args()

    if not os.path.isdir(args.thesis_refs):
        print(json.dumps({"error": f"thesis-refs not found: {args.thesis_refs}"}))
        sys.exit(1)

    active = index_active_notes(args.vault_refs) if os.path.isdir(args.vault_refs) else {}

    plan = []
    for root, dirs, files in os.walk(args.thesis_refs):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        topic = os.path.relpath(root, args.thesis_refs)
        topic = "" if topic == "." else topic
        for f in sorted(files):
            if not f.lower().endswith(".pdf"):
                continue
            if args.article and args.article.lower() not in f.lower():
                continue
            author_key, display, year = parse_pdf_name(f)
            key = f"{author_key}_{year}"
            note_path = active.get(key)
            n_cards = 0
            if note_path:
                try:
                    with open(note_path, encoding="utf-8") as fh:
                        n_cards = has_flashcards(fh.read())
                except OSError:
                    pass
            if not note_path:
                action = "create"
            elif n_cards == 0:
                action = "add_cards"
            else:
                action = "skip"
            plan.append({
                "topic": topic,
                "pdf": os.path.join(root, f),
                "author": display,
                "year": year,
                "key": key,
                "note_exists": bool(note_path),
                "note_path": note_path,
                "n_cards": n_cards,
                "action": action,
                # where a NEW note should be written (mirrors the topic subfolder)
                "target_note": os.path.join(
                    args.vault_refs, topic, f"{display} {year} - Notes.md"
                ),
            })

    summary = {"create": 0, "add_cards": 0, "skip": 0}
    for p in plan:
        summary[p["action"]] += 1
    print(json.dumps({"summary": summary, "plan": plan}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
