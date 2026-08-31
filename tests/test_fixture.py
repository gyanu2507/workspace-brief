import json
from pathlib import Path

from workspace_brief.fixture import get_issue, search_issues, search_notes


def test_promo_issue_is_41():
    hits = search_issues("empty promo checkout 500")
    assert hits[0]["number"] == 41


def test_get_issue():
    assert get_issue(38)["title"].lower().startswith("webhook")
    assert get_issue(9999) is None


def test_incident_note():
    hits = search_notes("duplicate invoices stripe")
    assert hits[0]["id"] == "note-aug-11-incident"


def test_fixture_files_present():
    root = Path(__file__).resolve().parents[1] / "fixtures" / "northstar"
    for name in ("issues.json", "pulls.json", "commits.json", "notes.json"):
        assert (root / name).exists()
