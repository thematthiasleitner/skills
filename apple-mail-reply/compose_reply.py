#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose a reply or a new outgoing message in Apple Mail via AppleScript.

Two modes:

* ``reply``  — find the most-recent message in ``--account``'s inbox whose
  subject contains ``--subject``, open a reply-all compose window via Mail's
  native ``reply`` (preserves quoted text + recipients), then write the
  prepared body to the clipboard so the user can paste with ⌘V. Attachments
  are added programmatically.
* ``new``    — create a new outgoing message with explicit recipients,
  subject, body, and attachments. The compose window is left visible; the
  body is set in-place (no clipboard needed since no native reply HTML
  competes with it).

In BOTH modes the compose window is left visible and NEVER programmatically
saved or sent. Mail's server-side sync race tends to land programmatic
saves in Trash; only the user's ⌘-S works reliably.

Today's three pitfalls this script encodes around::

  1. `reply origMsg opening yes with reply to all` is a syntax error.
     The correct form is `reply origMsg with opening window and reply to all`.
  2. Programmatic `set content to ...` on a reply doesn't survive a
     subsequent save — the HTML body wins. Workaround: clipboard.
  3. Programmatic `save` of a new outgoing message can drop the message
     into Trash. Workaround: never save; let the user ⌘-S.

Usage::

    # reply mode
    compose_reply.py reply \\
        --subject "ADVANCE - Documents for the german translation" \\
        --body "Hi Pieter,\\n\\nPlease find attached:..." \\
        --attach /path/to/file1.json /path/to/file2.docx \\
        [--account UNIGE] [--no-cc]

    # new-message mode
    compose_reply.py new \\
        --to pieter@ippo.nl \\
        --cc Melanie.Mack@unige.ch \\
        --subject "Re: ADVANCE - Documents for the german translation" \\
        --body "Hi Pieter, ..." \\
        --attach /path/to/file.json \\
        [--account UNIGE]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional


# Mailbox-name candidates by role, ordered by preference. Apple Mail's
# localization differs per account/region; we try the user's likely
# names in order and use the first that exists.
INBOX_NAMES = ("Boîte de réception", "Inbox", "Posteingang")
DRAFTS_NAMES = ("Brouillons", "Drafts", "Entwürfe")


def _applescript_escape(s: str) -> str:
    """Escape a string for embedding inside AppleScript double quotes."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _run_osascript(script: str) -> tuple[int, str, str]:
    """Write the script to a temp file (so multi-line strings survive the
    shell boundary) and run it. Returns (rc, stdout, stderr)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".applescript", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        path = f.name
    try:
        cp = subprocess.run(
            ["osascript", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _resolve_attachments(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for p in paths or []:
        ap = Path(p).expanduser().resolve()
        if not ap.exists():
            raise SystemExit(f"attachment not found: {ap}")
        if not ap.is_file():
            raise SystemExit(f"attachment is not a file: {ap}")
        out.append(ap)
    return out


def _attachment_clauses(attachments: List[Path]) -> str:
    if not attachments:
        return ""
    lines = []
    for ap in attachments:
        ap_esc = _applescript_escape(str(ap))
        lines.append(
            f'            make new attachment with properties '
            f'{{file name:(POSIX file "{ap_esc}") as alias}} '
            f"at after the last paragraph"
        )
    return "\n".join(lines)


def reply_script(
    account: str,
    subject_substring: str,
    body: str,
    attachments: List[Path],
    reply_to_all: bool,
) -> str:
    """Generate AppleScript for REPLY mode.

    Strategy: find newest message by subject substring → open native reply
    window (preserves recipients + quoted text) → set clipboard to our body
    → leave window visible. User pastes (⌘V) into the body and presses ⌘-S
    or ⌘-↩.
    """
    account_e = _applescript_escape(account)
    subject_e = _applescript_escape(subject_substring)
    body_e = _applescript_escape(body)
    reply_flag = "and reply to all" if reply_to_all else ""
    inbox_candidates = ", ".join(f'"{_applescript_escape(n)}"' for n in INBOX_NAMES)
    att_block = _attachment_clauses(attachments)

    return f'''
tell application "Mail"
    activate
    set theAcct to first account whose name is "{account_e}"

    -- find the inbox mailbox (localized name)
    set inboxMbx to missing value
    repeat with cand in {{{inbox_candidates}}}
        try
            set inboxMbx to (mailbox (cand as text) of theAcct)
            exit repeat
        end try
    end repeat
    if inboxMbx is missing value then
        return "ERROR: could not find inbox mailbox in account {account_e}"
    end if

    -- find candidate messages
    set candidates to (messages of inboxMbx whose subject contains "{subject_e}")
    if (count of candidates) is 0 then
        return "ERROR: no messages with subject containing \\"{subject_e}\\" in account {account_e}"
    end if

    -- pick newest by date received
    set newestMsg to item 1 of candidates
    set newestDate to date received of newestMsg
    repeat with m in candidates
        if (date received of m) > newestDate then
            set newestMsg to m
            set newestDate to date received of m
        end if
    end repeat

    set matchInfo to "matched " & (count of candidates) & " message(s); using newest from " & ((sender of newestMsg) as text) & " at " & (newestDate as string)

    -- copy prepared body to clipboard so user can paste in compose window
    set the clipboard to "{body_e}"

    -- open native reply window (preserves recipients + quoted text)
    set theReply to reply newestMsg with opening window {reply_flag}
    delay 1.5

    -- add attachments
    tell theReply
        tell content
{att_block}
        end tell
    end tell

    return "OK | " & matchInfo
end tell
'''


def new_message_script(
    account: str,
    to: List[str],
    cc: List[str],
    subject: str,
    body: str,
    attachments: List[Path],
) -> str:
    """Generate AppleScript for NEW-message mode.

    Sets content + recipients + attachments in one shot. Window stays
    visible. Body is set directly (no clipboard needed) since there is
    no competing native HTML body.
    """
    account_e = _applescript_escape(account)
    subject_e = _applescript_escape(subject)
    body_e = _applescript_escape(body)

    to_clauses = "\n".join(
        f'        make new to recipient at end of to recipients '
        f'with properties {{address:"{_applescript_escape(addr)}"}}'
        for addr in to
    )
    cc_clauses = "\n".join(
        f'        make new cc recipient at end of cc recipients '
        f'with properties {{address:"{_applescript_escape(addr)}"}}'
        for addr in cc
    )
    att_block = _attachment_clauses(attachments)

    return f'''
tell application "Mail"
    activate
    set theAcct to first account whose name is "{account_e}"

    -- create new outgoing message scoped to the requested account by
    -- setting `sender` to one of its email addresses (the first one).
    set theAddrs to email addresses of theAcct
    if (count of theAddrs) is 0 then
        return "ERROR: account {account_e} has no email addresses configured"
    end if
    set primarySender to item 1 of theAddrs

    set newMsg to make new outgoing message with properties {{subject:"{subject_e}", content:"{body_e}", sender:primarySender, visible:true}}

    tell newMsg
{to_clauses}
{cc_clauses}
        tell content
{att_block}
        end tell
    end tell

    return "OK | new message composed, window visible"
end tell
'''


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    pr = sub.add_parser("reply", help="Reply to a thread by subject substring.")
    pr.add_argument("--subject", required=True,
                    help="Substring of the subject to find.")
    pr.add_argument("--body", required=True,
                    help="Body text. Will be placed on the clipboard for the user to ⌘V into the compose window.")
    pr.add_argument("--attach", nargs="*", default=[],
                    help="One or more file paths to attach.")
    pr.add_argument("--account", default="UNIGE",
                    help="Mail account name. Default: UNIGE.")
    pr.add_argument("--no-cc", action="store_true",
                    help="Reply to sender only, not reply-all.")

    pn = sub.add_parser("new", help="Compose a new outgoing message.")
    pn.add_argument("--to", nargs="+", required=True,
                    help="One or more To: addresses.")
    pn.add_argument("--cc", nargs="*", default=[],
                    help="Zero or more Cc: addresses.")
    pn.add_argument("--subject", required=True)
    pn.add_argument("--body", required=True)
    pn.add_argument("--attach", nargs="*", default=[])
    pn.add_argument("--account", default="UNIGE",
                    help="Mail account name. Default: UNIGE.")

    args = parser.parse_args(argv)

    attachments = _resolve_attachments(args.attach)

    if args.mode == "reply":
        script = reply_script(
            account=args.account,
            subject_substring=args.subject,
            body=args.body,
            attachments=attachments,
            reply_to_all=not args.no_cc,
        )
    else:
        script = new_message_script(
            account=args.account,
            to=args.to,
            cc=args.cc,
            subject=args.subject,
            body=args.body,
            attachments=attachments,
        )

    rc, out, err = _run_osascript(script)
    if rc != 0 or out.startswith("ERROR"):
        print(f"osascript rc={rc}", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        if out:
            print(out, file=sys.stderr)
        return 1 if not out.startswith("ERROR") else 2

    print(out)
    print()
    if args.mode == "reply":
        print("Body has been copied to the clipboard. Switch to the open compose")
        print("window, click in the body above the quoted text, and ⌘V to paste.")
        print(f"Attachments added: {len(attachments)}")
    else:
        print(f"To: {', '.join(args.to)}")
        if args.cc:
            print(f"Cc: {', '.join(args.cc)}")
        print(f"Attachments added: {len(attachments)}")
    print()
    print("The compose window is visible. Review, then ⌘-S to save as draft or ⌘-⇧-D to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
