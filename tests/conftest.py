import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("BRIEF_MEMORY_PATH", str(tmp_path / "mem.sqlite"))
    monkeypatch.setenv("BRIEF_TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("BRIEF_SOURCE", "fixture")
    monkeypatch.delenv("BRIEF_REPO", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
