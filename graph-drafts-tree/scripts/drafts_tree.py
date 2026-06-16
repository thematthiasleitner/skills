#!/usr/bin/env python3
"""Print a Microsoft Graph mail-folder tree (counts, subjects, optional body grep).

Read-only. Designed for the ADVANCE mailbox but works on any folder subtree
reachable via the repo's GraphMailService.

Run from an email_draft_automation checkout that has a live Graph token
(typically the server):

    set -a; source .env; set +a
    PYTHONPATH=$HOME .venv/bin/python3 drafts_tree.py                 # Drafts/hardcoded
    PYTHONPATH=$HOME .venv/bin/python3 drafts_tree.py _test_drafts hardcoded
    PYTHONPATH=$HOME .venv/bin/python3 drafts_tree.py --grep SV_42W7wVwedBnaUB0

Positional args are folder segments under Drafts. --subjects lists each
message subject; --grep PATTERN scans message bodies and exits 1 when any
hit is found (so sweeps can assert a tree is clean).

Gotcha encoded here: the mailFolder $select property is ``totalItemCount``
(``totalChildItemCount`` does NOT exist and 400s the request).
"""

from __future__ import annotations

import argparse
import os
import sys

FOLDER_SELECT = "id,displayName,totalItemCount,childFolderCount"


def walk(fetch_children, fetch_messages, root_id, root_name,
         grep=None, show_subjects=False):
    """Pure tree walk. Returns (lines, hits).

    fetch_children(folder_id) -> [{id, displayName, totalItemCount,
                                   childFolderCount}]
    fetch_messages(folder_id) -> [{subject, body, to}]  (body/to optional)
    hits: [(path, subject, to, count)] for bodies containing ``grep``.

    Scans the named root folder's OWN messages as well as every descendant, so
    scoping a sweep directly at a leaf folder (one that holds messages but has
    no subfolders) is not a silent no-op. Previously only child folders were
    walked, so a leaf-scoped ``--grep`` scanned nothing and falsely read clean.
    """
    lines, hits = [], []
    want_msgs = bool(show_subjects or grep)

    def scan_messages(fid, path, indent):
        for m in fetch_messages(fid):
            if show_subjects:
                lines.append(f"{indent}- {m.get('subject', '')}")
            if grep:
                c = (m.get("body") or "").count(grep)
                if c:
                    hits.append((path, m.get("subject", ""),
                                 m.get("to", ""), c))

    def rec(fid, name, depth, path):
        indent = "  " * depth
        for f in fetch_children(fid):
            cname = f["displayName"]
            cpath = f"{path}/{cname}"
            n = f.get("totalItemCount") or 0
            lines.append(f"{indent}{cname}/  ({n})")
            if f.get("childFolderCount"):
                rec(f["id"], cname, depth + 1, cpath)
            if n and want_msgs:
                scan_messages(f["id"], cpath, indent + "  ")

    lines.append(f"{root_name}/")
    if want_msgs:
        scan_messages(root_id, root_name, "  ")
    rec(root_id, root_name, 1, root_name)
    return lines, hits


def graph_fetchers(mail, want_bodies):
    """Real Graph-backed fetchers for the walk()."""
    msg_select = "id,subject,toRecipients" + (",body" if want_bodies else "")

    def fetch_children(fid):
        resp = mail._request(  # noqa: SLF001
            "GET", f"/users/{mail.mailbox}/mailFolders/{fid}/childFolders",
            params={"$top": 200, "$select": FOLDER_SELECT},
        )
        return resp.json().get("value", [])

    def fetch_messages(fid):
        resp = mail._request(  # noqa: SLF001
            "GET", f"/users/{mail.mailbox}/mailFolders/{fid}/messages",
            params={"$top": 200, "$select": msg_select},
        )
        out = []
        for m in resp.json().get("value", []):
            out.append({
                "subject": m.get("subject", ""),
                "body": (m.get("body") or {}).get("content", ""),
                "to": ";".join(r.get("emailAddress", {}).get("address", "")
                               for r in (m.get("toRecipients") or [])),
            })
        return out

    return fetch_children, fetch_messages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("segments", nargs="*", default=None,
                    help="folder segments under Drafts (default: hardcoded)")
    ap.add_argument("--grep", help="scan bodies; exit 1 if pattern found")
    ap.add_argument("--subjects", action="store_true",
                    help="list message subjects per folder")
    args = ap.parse_args()
    segments = args.segments or ["hardcoded"]

    sys.path.insert(0, os.path.expanduser("~"))
    from email_draft_automation.src.graph_mail import (  # noqa: PLC0415
        build_graph_service_from_env,
    )
    mail = build_graph_service_from_env()
    root_id = mail.resolve_draft_subfolder(*segments)
    fc, fm = graph_fetchers(mail, want_bodies=bool(args.grep))
    lines, hits = walk(fc, fm, root_id, "/".join(segments),
                       grep=args.grep, show_subjects=args.subjects)
    print("\n".join(lines))
    if args.grep:
        print(f"\ngrep '{args.grep}': {len(hits)} message(s) with hits")
        for path, subject, to, count in hits:
            print(f"  {path}  [{to}]  '{subject[:50]}'  x{count}")
        return 1 if hits else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
