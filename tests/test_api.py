from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from workspace_brief.api import app, limiter
from workspace_brief.fixture import fixture_dir
from workspace_brief.mcp_server import encode_message, handle, read_message


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    h = r.json()
    assert h["ok"] is True
    assert "version" in h
    assert r.headers.get("X-Request-Id")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_ready():
    r = TestClient(app).get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["memory"] == "ok"


def test_brief_fixture():
    r = TestClient(app).post("/brief", json={"question": "empty promo crash"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fixture"
    assert body["citations"]
    assert body["trace"]
    assert "/" not in body["trace"]
    assert Path(body["trace"]).name == body["trace"]


def test_root_and_health_have_version():
    c = TestClient(app)
    assert c.get("/").json()["name"] == "workspace-brief"
    h = c.get("/health").json()
    assert h["ok"] is True
    assert "version" in h


def test_api_key_required(monkeypatch):
    monkeypatch.setenv("BRIEF_API_KEY", "secret-key")
    c = TestClient(app)
    assert c.post("/brief", json={"question": "promo"}).status_code == 401
    ok = c.post(
        "/brief",
        json={"question": "empty promo crash"},
        headers={"X-API-Key": "secret-key"},
    )
    assert ok.status_code == 200
    bearer = c.post(
        "/brief",
        json={"question": "empty promo crash"},
        headers={"Authorization": "Bearer secret-key"},
    )
    assert bearer.status_code == 200


def test_allowlist_blocks_other_repos(monkeypatch):
    monkeypatch.setenv("BRIEF_ALLOWED_REPOS", "acme/app")
    r = TestClient(app).post(
        "/brief",
        json={"question": "what landed", "source": "github", "repo": "other/repo"},
    )
    assert r.status_code == 403


def test_rate_limit(monkeypatch):
    monkeypatch.setenv("BRIEF_RATE_LIMIT", "1")
    limiter.reset()
    c = TestClient(app)
    assert c.post("/brief", json={"question": "empty promo crash"}).status_code == 200
    limited = c.post("/brief", json={"question": "empty promo crash"})
    assert limited.status_code == 429
    assert limited.headers.get("retry-after") == "60"
    limiter.reset()


def test_packaged_fixture_exists():
    assert (fixture_dir() / "issues.json").is_file()


def test_github_without_repo_is_400():
    r = TestClient(app).post(
        "/brief",
        json={"question": "what landed", "source": "github"},
    )
    assert r.status_code == 400


def test_mcp_content_length_roundtrip():
    msg = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    raw = encode_message(msg)
    assert raw.startswith(b"Content-Length:")
    assert read_message(BytesIO(raw)) == msg


def test_mcp_newline_json_still_works():
    got = read_message(BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n'))
    assert got["method"] == "ping"


def test_framed_initialize():
    req = encode_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    msg = read_message(BytesIO(req))
    out = handle(msg)
    assert out["result"]["serverInfo"]["name"] == "workspace-brief"
    framed = encode_message(out)
    parsed = read_message(BytesIO(framed))
    assert parsed["result"]["protocolVersion"] == "2024-11-05"


def test_bad_session_is_422():
    r = TestClient(app).post("/brief", json={"question": "promo", "session": "../etc"})
    assert r.status_code == 422


def test_production_requires_api_key(monkeypatch):
    from workspace_brief.config import settings

    monkeypatch.setenv("BRIEF_ENV", "production")
    monkeypatch.delenv("BRIEF_API_KEY", raising=False)
    try:
        settings().require_serve()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "BRIEF_API_KEY" in str(e)


def test_production_github_needs_allowlist(monkeypatch):
    from workspace_brief.config import settings

    monkeypatch.setenv("BRIEF_ENV", "production")
    monkeypatch.setenv("BRIEF_API_KEY", "sixteen-chars-min")
    monkeypatch.setenv("BRIEF_SOURCE", "github")
    monkeypatch.delenv("BRIEF_ALLOWED_REPOS", raising=False)
    try:
        settings().require_serve()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "ALLOWED_REPOS" in str(e)


def test_production_hides_github_errors(monkeypatch):
    from workspace_brief.github import GithubError

    monkeypatch.setenv("BRIEF_ENV", "production")
    monkeypatch.setenv("BRIEF_API_KEY", "sixteen-chars-min")

    def boom(*args, **kwargs):
        raise GithubError("token ghp_shouldnotleak1234567890")

    monkeypatch.setattr("workspace_brief.api.run", boom)
    r = TestClient(app).post(
        "/brief",
        json={"question": "what landed", "source": "github", "repo": "acme/app"},
        headers={"X-API-Key": "sixteen-chars-min"},
    )
    assert r.status_code == 502
    assert r.json()["detail"] == "github upstream error"
    assert "ghp_" not in r.json()["detail"]
