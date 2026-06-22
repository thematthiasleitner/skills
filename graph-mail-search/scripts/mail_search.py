#!/usr/bin/env python3
"""Mailbox-wide Microsoft Graph $search: every message matching a term, across ALL folders.

Read-only. Finds messages anywhere the mailbox content index covers — Drafts
(including loose / manually-composed drafts that live OUTSIDE Drafts/hardcoded),
SentItems, Archive, Deleted Items. This is the "is there ANY mail to/from X,
anywhere?" tool. It complements:

  - graph-drafts-tree   — walks the Drafts/hardcoded subtree, body-grep only
  - graph-sentitems-scan — walks SentItems by date range only

Run from an email_draft_automation checkout with a LIVE Graph token (typically
the server; local ms_token.json caches are usually stale):

    set -a; source .env; set +a
    PYTHONPATH=$HOME .venv/bin/python3 mail_search.py "e.bruder01@bluewin.ch"
    PYTHONPATH=$HOME .venv/bin/python3 mail_search.py "Bruder" "e.bruder01@bluewin.ch"
    PYTHONPATH=$HOME .venv/bin/python3 mail_search.py --expect-empty "e.bruder01@bluewin.ch"

Each positional arg is a search term; results are printed per term (folder name,
isDraft, sent/recv/mod timestamps, from/to, subject). With --expect-empty the
script exits 1 if ANY term has hits (so a sweep can assert a mailbox is clean),
mirroring graph-drafts-tree --grep semantics.

Two traps encoded here:
  * $search on /messages REQUIRES the ``ConsistencyLevel: eventual`` header
    (passed via ``_request(consistency="eventual")``). Without it Graph may 400
    or silently ignore the search term.
  * $search covers all *visible* folders but NOT the Recoverable Items dumpster
    ("Recover items recently removed from this folder"). A hard-deleted message
    will read as absent here — say so when reporting "0 found".
"""

from __future__ import annotations

import argparse
import os
import sys

MSG_SELECT = (
    "subject,isDraft,parentFolderId,sentDateTime,"
    "receivedDateTime,lastModifiedDateTime,from,toRecipients"
)


def search(fetch_messages, resolve_folder, term):
    """Pure formatting core. Returns (count, lines).

    fetch_messages(term) -> [message dict in Graph shape]
    resolve_folder(folder_id) -> display name (str)

    Tolerates missing fields (a draft has no sentDateTime; a message may have no
    from/toRecipients) without raising.
    """
    vals = fetch_messages(term) or []
    lines = [f"=== $search {term!r}: {len(vals)} message(s) across ALL folders ==="]
    for m in vals:
        to = ";".join(
            r.get("emailAddress", {}).get("address", "")
            for r in (m.get("toRecipients") or [])
        )
        frm = (m.get("from") or {}).get("emailAddress", {}).get("address", "")
        lines.append(
            f"- folder={resolve_folder(m.get('parentFolderId'))!r} "
            f"isDraft={m.get('isDraft')} sent={m.get('sentDateTime')} "
            f"recv={m.get('receivedDateTime')} mod={m.get('lastModifiedDateTime')}"
        )
        lines.append(f"    from={frm} to={to}")
        lines.append(f"    subj={(m.get('subject') or '')[:70]!r}")
    return len(vals), lines


def graph_fetchers(mail):
    """Real Graph-backed fetchers for search()."""
    mbx = mail.mailbox
    cache = {}

    def resolve_folder(fid):
        if not fid:
            return "?"
        if fid not in cache:
            try:
                resp = mail._request(  # noqa: SLF001
                    "GET", f"/users/{mbx}/mailFolders/{fid}",
                    params={"$select": "displayName,id"},
                )
                cache[fid] = resp.json().get("displayName", fid)
            except Exception:
                cache[fid] = f"?{str(fid)[:10]}"
        return cache[fid]

    def fetch_messages(term):
        resp = mail._request(  # noqa: SLF001
            "GET", f"/users/{mbx}/messages",
            params={"$search": f'"{term}"', "$select": MSG_SELECT, "$top": 100},
            consistency="eventual",
        )
        return resp.json().get("value", [])

    return fetch_messages, resolve_folder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("terms", nargs="+", help="search term(s) — address, surname, link…")
    ap.add_argument("--expect-empty", action="store_true",
                    help="exit 1 if ANY term has hits (assert mailbox is clean)")
    args = ap.parse_args()

    sys.path.insert(0, os.path.expanduser("~"))
    from email_draft_automation.src.graph_mail import (  # noqa: PLC0415
        build_graph_service_from_env,
    )

    mail = build_graph_service_from_env()
    fetch_messages, resolve_folder = graph_fetchers(mail)

    total = 0
    for term in args.terms:
        count, lines = search(fetch_messages, resolve_folder, term)
        print("\n".join(lines))
        print()
        total += count

    print(f"TOTAL across {len(args.terms)} term(s): {total} message(s). "
          "(NB: $search does not reach the Recoverable Items dumpster.)")
    if args.expect_empty:
        return 1 if total else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
