import json
from pathlib import Path

from workspace_brief.cli import main
from workspace_brief.github import GithubError


def test_help_without_question():
    assert main([]) == 1


def test_github_needs_repo():
    assert main(["--source", "github", "anything"]) == 2


def test_github_error_exits_3(monkeypatch):
    def boom(*args, **kwargs):
        raise GithubError("github 502")

    monkeypatch.setattr("workspace_brief.cli.run", boom)
    assert main(["--source", "github", "--repo", "acme/app", "what landed"]) == 3


def test_fixture_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # fixture files live in the repo, not cwd; search still works
    rc = main(["--trace-dir", str(tmp_path / "t"), "empty promo crash"])
    assert rc == 0
    traces = list((tmp_path / "t").glob("*.json"))
    assert traces


def test_json_output(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = main(["--json", "--trace-dir", str(tmp_path / "t"), "empty promo crash"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["source"] == "fixture"
    assert data["citations"]
    assert data["trace"]
