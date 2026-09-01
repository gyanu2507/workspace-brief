from workspace_brief.mcp_server import handle


def test_initialize():
    r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r["result"]["serverInfo"]["name"] == "workspace-brief"


def test_tools_list():
    r = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in r["result"]["tools"]}
    assert {"search_issues", "get_issue", "search_pulls", "list_commits", "search_notes"} <= names


def test_call_search_issues():
    r = handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search_issues", "arguments": {"query": "promo"}},
        }
    )
    assert r["result"]["isError"] is False
    assert "#41" in r["result"]["content"][0]["text"] or "41" in r["result"]["content"][0]["text"]


def test_initialized_is_silent():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
