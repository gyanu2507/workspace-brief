from __future__ import annotations

import os

import httpx

from workspace_brief.retrieve import rank

API = "https://api.github.com"


class GithubError(RuntimeError):
    pass


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "workspace-brief",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, params: dict | None = None):
    with httpx.Client(base_url=API, headers=_headers(), timeout=25) as c:
        r = c.get(path, params=params)
    if r.status_code == 403:
        raise GithubError("github rate-limited; set GITHUB_TOKEN")
    if r.status_code == 404:
        raise GithubError(f"not found: {path}")
    r.raise_for_status()
    return r.json()


def _issue_shape(raw: dict) -> dict:
    # the issues listing also contains pulls
    return {
        "number": raw["number"],
        "title": raw.get("title") or "",
        "state": raw.get("state") or "",
        "labels": [lb["name"] if isinstance(lb, dict) else str(lb) for lb in raw.get("labels") or []],
        "author": (raw.get("user") or {}).get("login"),
        "updated": (raw.get("updated_at") or "")[:10],
        "body": raw.get("body") or "",
        "url": raw.get("html_url"),
    }


def search_issues(repo: str, query: str, n: int = 5) -> list:
    owner, name = repo.split("/", 1)
    raw = _get(f"/repos/{owner}/{name}/issues", params={"state": "all", "per_page": 50})
    items = [_issue_shape(x) for x in raw if "pull_request" not in x]
    return rank(query, items, n)


def get_issue(repo: str, number: int) -> dict | None:
    owner, name = repo.split("/", 1)
    try:
        raw = _get(f"/repos/{owner}/{name}/issues/{number}")
    except GithubError:
        return None
    if "pull_request" in raw:
        return None
    return _issue_shape(raw)


def search_pulls(repo: str, query: str, n: int = 5) -> list:
    owner, name = repo.split("/", 1)
    raw = _get(f"/repos/{owner}/{name}/pulls", params={"state": "all", "per_page": 50})
    items = []
    for x in raw:
        items.append(
            {
                "number": x["number"],
                "title": x.get("title") or "",
                "state": "merged" if x.get("merged_at") else x.get("state") or "",
                "author": (x.get("user") or {}).get("login"),
                "updated": (x.get("updated_at") or "")[:10],
                "body": x.get("body") or "",
                "url": x.get("html_url"),
            }
        )
    return rank(query, items, n)


def list_commits(repo: str, n: int = 8) -> list:
    owner, name = repo.split("/", 1)
    raw = _get(f"/repos/{owner}/{name}/commits", params={"per_page": n})
    out = []
    for x in raw:
        sha = x.get("sha") or ""
        commit = x.get("commit") or {}
        out.append(
            {
                "sha": sha[:7],
                "date": ((commit.get("author") or {}).get("date") or "")[:10],
                "author": (x.get("author") or {}).get("login") or (commit.get("author") or {}).get("name"),
                "message": (commit.get("message") or "").split("\n", 1)[0],
                "url": x.get("html_url"),
            }
        )
    return out


def search_notes(repo: str, query: str, n: int = 5) -> list:
    # no notes on github, reuse issues so the agent has somewhere to look
    return search_issues(repo, query, n)
