"""Hermetic tests for the drafts_tree walk logic (no Graph, no network).

Run:  python3 -m pytest ~/.claude/skills/graph-drafts-tree/test_drafts_tree.py -q
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))

from drafts_tree import FOLDER_SELECT, walk  # noqa: E402

# Fake mailbox: root → part/ (prog_info_standard with 2 msgs), part_PC/ (empty)
FOLDERS = {
    "root": [
        {"id": "f-part", "displayName": "part",
         "totalItemCount": 0, "childFolderCount": 1},
        {"id": "f-pc", "displayName": "part_PC",
         "totalItemCount": 0, "childFolderCount": 0},
    ],
    "f-part": [
        {"id": "f-pis", "displayName": "prog_info_standard",
         "totalItemCount": 2, "childFolderCount": 0},
    ],
    "f-pis": [],
    "f-pc": [],
}
MESSAGES = {
    "f-pis": [
        {"subject": "[Template demo] prog_info_standard (DE)",
         "body": "hello SV_OLDLINK world", "to": "tmpl-a@advance-test.invalid"},
        {"subject": "[Template demo] prog_info_standard (FR)",
         "body": "bonjour, rien", "to": "tmpl-a@advance-test.invalid"},
    ],
}

fetch_children = lambda fid: FOLDERS.get(fid, [])  # noqa: E731
fetch_messages = lambda fid: MESSAGES.get(fid, [])  # noqa: E731


def test_tree_lines_show_counts_and_nesting():
    lines, hits = walk(fetch_children, fetch_messages, "root", "hardcoded")
    assert lines[0] == "hardcoded/"
    assert "  part/  (0)" in lines
    assert "    prog_info_standard/  (2)" in lines
    assert "  part_PC/  (0)" in lines
    assert hits == []


def test_subjects_listed_when_requested():
    lines, _ = walk(fetch_children, fetch_messages, "root", "hardcoded",
                    show_subjects=True)
    assert any("prog_info_standard (DE)" in ln for ln in lines)
    assert any("prog_info_standard (FR)" in ln for ln in lines)


def test_grep_reports_hits_with_path_and_count():
    _, hits = walk(fetch_children, fetch_messages, "root", "hardcoded",
                   grep="SV_OLDLINK")
    assert hits == [("hardcoded/part/prog_info_standard",
                     "[Template demo] prog_info_standard (DE)",
                     "tmpl-a@advance-test.invalid", 1)]


def test_grep_clean_tree_returns_no_hits():
    _, hits = walk(fetch_children, fetch_messages, "root", "hardcoded",
                   grep="NOT_PRESENT")
    assert hits == []


def test_folder_select_uses_existing_graph_property():
    # totalChildItemCount does not exist on mailFolder — Graph 400s on it.
    assert "totalItemCount" in FOLDER_SELECT
    assert "totalChildItemCount" not in FOLDER_SELECT


# Regression: scoping a sweep directly at a LEAF folder (holds messages, no
# child folders) must still scan those messages. This was a silent no-op —
# walk() only scanned child folders, so a leaf-scoped --grep read "0 hits /
# clean" without ever looking at a single body.
LEAF_NO_CHILDREN = lambda fid: []  # noqa: E731
LEAF_MESSAGES = lambda fid: [  # noqa: E731
    {"subject": "consent invite", "body": "go to SV_NEWLINK now",
     "to": "p@example.ch"},
    {"subject": "other", "body": "nothing here", "to": "q@example.ch"},
]


def test_grep_scans_leaf_root_folder_messages():
    _, hits = walk(LEAF_NO_CHILDREN, LEAF_MESSAGES, "leaf",
                   "consent_pre_invite", grep="SV_NEWLINK")
    assert hits == [("consent_pre_invite", "consent invite",
                     "p@example.ch", 1)]


def test_subjects_listed_for_leaf_root_folder():
    lines, _ = walk(LEAF_NO_CHILDREN, LEAF_MESSAGES, "leaf",
                    "consent_pre_invite", show_subjects=True)
    assert lines[0] == "consent_pre_invite/"
    assert any("consent invite" in ln for ln in lines)
