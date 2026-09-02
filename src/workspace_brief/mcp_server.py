"""stdio MCP wrapping the same tools the CLI uses.

Speaks the MCP transport (Content-Length headers). Newline JSON still
works for tests and `echo '{...}' | python -m workspace_brief.mcp_server`.

  python -m workspace_brief.mcp_server

BRIEF_SOURCE=github BRIEF_REPO=owner/name for a live repo.
"""
from __future__ import annotations

import json
import sys

from workspace_brief import __version__
from workspace_brief.config import settings, setup_logging
from workspace_brief.redact import redact
from workspace_brief.sources import get_source


def _src():
    cfg = settings()
    return get_source(cfg.default_source, cfg.default_repo)


TOOLS = [
    {
        "name": "search_issues",
        "description": "Search workspace issues by free text.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_issue",
        "description": "Fetch one issue by number.",
        "inputSchema": {
            "type": "object",
            "properties": {"number": {"type": "integer"}},
            "required": ["number"],
        },
    },
    {
        "name": "search_pulls",
        "description": "Search pull requests by free text.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "list_commits",
        "description": "Recent commits, newest first.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_notes",
        "description": "Search internal notes (fixture only; GitHub reuses issues).",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def _call(name: str, args: dict):
    src = _src()
    if name == "search_issues":
        return src.search_issues(args["query"])
    if name == "get_issue":
        return src.get_issue(int(args["number"]))
    if name == "search_pulls":
        return src.search_pulls(args["query"])
    if name == "list_commits":
        return src.list_commits()
    if name == "search_notes":
        return src.search_notes(args["query"])
    raise ValueError(f"unknown tool {name}")


def _result(id_, payload):
    return {"jsonrpc": "2.0", "id": id_, "result": payload}


def handle(msg: dict) -> dict | None:
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        return _result(
            mid,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "workspace-brief", "version": __version__},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(mid, {"tools": TOOLS})
    if method == "ping":
        return _result(mid, {})
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            data = _call(name, args)
            text = json.dumps(data, indent=2)
            return _result(
                mid,
                {"content": [{"type": "text", "text": text}], "isError": False},
            )
        except Exception as e:
            return _result(
                mid,
                {"content": [{"type": "text", "text": redact(str(e))}], "isError": True},
            )
    if mid is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"unknown method {method}"},
    }


def encode_message(msg: dict) -> bytes:
    body = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def read_message(buf) -> dict | None:
    """Read one JSON-RPC message. Accepts MCP framing or a single JSON line."""
    header_bytes = b""
    while True:
        line = buf.readline()
        if not line:
            return None
        if line.startswith(b"{") or line.startswith(b"["):
            return json.loads(line)
        if line in (b"\r\n", b"\n"):
            break
        header_bytes += line
    headers = {}
    for raw in header_bytes.decode("ascii", errors="replace").splitlines():
        if ":" in raw:
            k, v = raw.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length") or 0)
    if n <= 0:
        return None
    body = buf.read(n)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def main() -> None:
    setup_logging()
    stdin = sys.stdin.buffer
    while True:
        try:
            msg = read_message(stdin)
        except json.JSONDecodeError:
            continue
        if msg is None:
            break
        out = handle(msg)
        if out is not None:
            sys.stdout.buffer.write(encode_message(out))
            sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
