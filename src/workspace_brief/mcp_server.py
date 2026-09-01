"""stdio MCP wrapping the same tools the CLI uses.

Run: python -m workspace_brief.mcp_server
Optional env: BRIEF_SOURCE=github BRIEF_REPO=owner/name
"""
from __future__ import annotations

import json
import sys

from workspace_brief.sources import get_source


def _src():
    import os

    kind = os.environ.get("BRIEF_SOURCE", "fixture")
    repo = os.environ.get("BRIEF_REPO")
    return get_source(kind, repo)


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
                "serverInfo": {"name": "workspace-brief", "version": "0.1.0"},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(mid, {"tools": TOOLS})
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
                {"content": [{"type": "text", "text": str(e)}], "isError": True},
            )
    if mid is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"unknown method {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
