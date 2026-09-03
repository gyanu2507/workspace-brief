from __future__ import annotations

import logging
import re
import time

from workspace_brief import __version__
from workspace_brief.config import settings
from workspace_brief.redact import redact
from workspace_brief.retrieve import rank

API = "https://api.github.com"
log = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 502, 503, 504}


class GithubError(RuntimeError):
    pass


class RepoNotAllowed(GithubError):
    pass


def _headers() -> dict:
    cfg = settings()
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"workspace-brief/{__version__}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if cfg.github_token:
        h["Authorization"] = f"Bearer {cfg.github_token}"
    return h


def _split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise GithubError("repo must be owner/name")
    owner, name = repo.split("/", 1)
    if not owner or not name or "/" in name:
        raise GithubError("repo must be owner/name")
    allowed = settings().allowed_repos
    if allowed and repo.lower() not in allowed:
        raise RepoNotAllowed(f"repo not allowed: {repo}")
    return owner, name


def _get(path: str, params: dict | None = None):
    import httpx

    cfg = settings()
    last_err = None
    for attempt in range(max(1, cfg.github_retries)):
        try:
            with httpx.Client(base_url=API, headers=_headers(), timeout=cfg.github_timeout) as c:
                r = c.get(path, params=params)
        except httpx.TransportError as e:
            last_err = GithubError(redact(str(e)))
            log.warning("github transport error attempt %s: %s", attempt + 1, last_err)
            time.sleep(min(2 ** attempt, 8))
            continue
        retry_after = r.headers.get("retry-after")
        if r.status_code in _RETRY_STATUSES or (r.status_code == 403 and retry_after):
            last_err = GithubError(f"github {r.status_code}")
            try:
                wait = float(retry_after) if retry_after else min(2 ** attempt, 8)
            except ValueError:
                wait = min(2 ** attempt, 8)
            wait = min(max(wait, 0), 30)
            log.warning("github %s, retry in %ss", r.status_code, wait)
            time.sleep(wait)
            continue
        if r.status_code == 403:
            raise GithubError("github rate-limited; set GITHUB_TOKEN")
        if r.status_code == 404:
            raise GithubError(f"not found: {path}")
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise GithubError(redact(str(e))) from None
        return r.json()
    raise last_err or GithubError("github request failed")


_SEARCH_NOISE = re.compile(r"[^\w.#/+ -]+")


def _search_q(query: str, qualifier: str) -> str:
    cleaned = _SEARCH_NOISE.sub(" ", query)
    cleaned = " ".join(cleaned.split())[:180]
    if not cleaned:
        cleaned = "is:open"
    return f"{cleaned} {qualifier}"


def _search_items(query: str, qualifier: str) -> list[dict] | None:
    """GitHub search hits, or None to fall back to listing the repo."""
    q = _search_q(query, qualifier)
    try:
        raw = _get("/search/issues", params={"q": q, "per_page": 20})
    except GithubError as e:
        msg = str(e).lower()
        if "rate-limited" in msg or "not found" in msg:
            raise
        log.warning("github search fallback: %s", e)
        return None
    if not isinstance(raw, dict):
        return None
    return list(raw.get("items") or [])


def _issue_shape(raw: dict) -> dict:
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


def _list_issues(owner: str, name: str) -> list[dict]:
    raw = _get(f"/repos/{owner}/{name}/issues", params={"state": "all", "per_page": 50})
    if not isinstance(raw, list):
        return []
    return [_issue_shape(x) for x in raw if isinstance(x, dict) and "pull_request" not in x]


def search_issues(repo: str, query: str, n: int = 5) -> list:
    owner, name = _split_repo(repo)
    found = _search_items(query, f"repo:{owner}/{name} is:issue")
    if found is not None:
        items = [_issue_shape(x) for x in found if "pull_request" not in x]
        ranked = rank(query, items, n)
        if ranked:
            return ranked
        if items:
            return items[:n]
    return rank(query, _list_issues(owner, name), n)


def get_issue(repo: str, number: int) -> dict | None:
    owner, name = _split_repo(repo)
    try:
        raw = _get(f"/repos/{owner}/{name}/issues/{number}")
    except GithubError:
        return None
    if "pull_request" in raw:
        return None
    return _issue_shape(raw)


def _pull_shape(raw: dict) -> dict:
    return {
        "number": raw["number"],
        "title": raw.get("title") or "",
        "state": "merged" if raw.get("merged_at") or raw.get("pull_request", {}).get("merged_at") else raw.get("state") or "",
        "author": (raw.get("user") or {}).get("login"),
        "updated": (raw.get("updated_at") or "")[:10],
        "body": raw.get("body") or "",
        "url": raw.get("html_url"),
    }


def search_pulls(repo: str, query: str, n: int = 5) -> list:
    owner, name = _split_repo(repo)
    found = _search_items(query, f"repo:{owner}/{name} is:pr")
    if found is not None:
        items = [_pull_shape(x) for x in found]
        ranked = rank(query, items, n)
        if ranked:
            return ranked
        if items:
            return items[:n]
    raw = _get(f"/repos/{owner}/{name}/pulls", params={"state": "all", "per_page": 50})
    return rank(query, [_pull_shape(x) for x in raw], n)


def list_commits(repo: str, n: int = 8) -> list:
    owner, name = _split_repo(repo)
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
    return search_issues(repo, query, n)
