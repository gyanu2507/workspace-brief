from workspace_brief.fixture import search_issues, search_notes, search_pulls
from workspace_brief.retrieve import rank


def test_promo_still_first():
    assert search_issues("empty promo checkout 500")[0]["number"] == 41


def test_zero_overlap_dropped():
    items = [{"title": "alpha", "body": "zzz"}, {"title": "beta", "body": "promo checkout"}]
    out = rank("promo checkout", items, n=5)
    assert [x["title"] for x in out] == ["beta"]


def test_pull_for_blank_promo():
    assert search_pulls("blank promo_code")[0]["number"] == 12


def test_incident_note():
    assert search_notes("11 august duplicate invoices")[0]["id"] == "note-aug-11-incident"
