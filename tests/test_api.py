from io import BytesIO

from fastapi.testclient import TestClient

from workspace_brief.api import app
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
