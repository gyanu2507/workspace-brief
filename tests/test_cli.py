from pathlib import Path

from workspace_brief.cli import main


def test_help_without_question():
    assert main([]) == 1


def test_github_needs_repo():
    assert main(["--source", "github", "anything"]) == 2


def test_fixture_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # fixture files live in the repo, not cwd; search still works
    rc = main(["--trace-dir", str(tmp_path / "t"), "empty promo crash"])
    assert rc == 0
    traces = list((tmp_path / "t").glob("*.json"))
    assert traces
