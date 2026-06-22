"""Hermetic tests for graph-mail-search/scripts/mail_search.py.

No network: the pure search() core is driven with fake fetchers. Mirrors the
fake-fetcher pattern in graph-drafts-tree/test_drafts_tree.py.

    python3 -m pytest ~/.claude/skills/graph-mail-search/test_mail_search.py -q
"""
import importlib.util
import pathlib

_PATH = pathlib.Path(__file__).parent / "scripts" / "mail_search.py"
_spec = importlib.util.spec_from_file_location("mail_search", _PATH)
mail_search = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mail_search)


def _msg(**kw):
    base = {
        "subject": "Anmeldebestätigung",
        "isDraft": True,
        "parentFolderId": "F1",
        "sentDateTime": None,
        "receivedDateTime": None,
        "lastModifiedDateTime": "2026-06-17T10:00:00Z",
        "from": {"emailAddress": {"address": "advance-project@unige.ch"}},
        "toRecipients": [{"emailAddress": {"address": "e.bruder01@bluewin.ch"}}],
    }
    base.update(kw)
    return base


def test_hit_is_counted_and_formatted():
    folders = {"F1": "registration_confirmation"}
    count, lines = mail_search.search(
        lambda t: [_msg()], lambda fid: folders.get(fid, "?"), "Bruder"
    )
    text = "\n".join(lines)
    assert count == 1
    assert "1 message(s)" in text
    assert "registration_confirmation" in text   # folder name resolved
    assert "e.bruder01@bluewin.ch" in text        # recipient surfaced
    assert "isDraft=True" in text
    assert "Anmeldebestätigung" in text           # subject surfaced


def test_empty_result_reads_clean():
    count, lines = mail_search.search(lambda t: [], lambda fid: "?", "nobody")
    assert count == 0
    assert "0 message(s)" in "\n".join(lines)


def test_none_result_does_not_crash():
    # a fetcher returning None (e.g. empty Graph payload) must be tolerated
    count, _ = mail_search.search(lambda t: None, lambda fid: "?", "x")
    assert count == 0


def test_missing_fields_do_not_raise():
    # a sparse message (no from / toRecipients / parentFolderId) must format
    count, lines = mail_search.search(
        lambda t: [{"subject": None, "parentFolderId": None}],
        lambda fid: "?",
        "x",
    )
    assert count == 1
    assert "to=" in "\n".join(lines)  # rendered an empty recipient list, no KeyError
