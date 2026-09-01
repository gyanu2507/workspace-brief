from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from workspace_brief.api import app, limiter
from workspace_brief.fixture import fixture_dir
from workspace_brief.mcp_server import encode_message, handle, read_message


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


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
    assert c.post("/brief", json={"question": "empty promo crash"}).status_code == 429
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
