import json
import re
from functools import lru_cache
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "northstar"


def _load(name: str):
    path = FIXTURE_DIR / name
    with path.open() as f:
        return json.load(f)


@lru_cache(maxsize=4)
def issues():
    return _load("issues.json")


@lru_cache(maxsize=4)
def pulls():
    return _load("pulls.json")


@lru_cache(maxsize=4)
def commits():
    return _load("commits.json")


@lru_cache(maxsize=4)
def notes():
    return _load("notes.json")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _blob(item: dict) -> str:
    parts = [str(v) for v in item.values() if v is not None]
    return " ".join(parts)


def _score(query: str, item: dict) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    t = _tokens(_blob(item))
    return len(q & t) / len(q)


def _rank(query: str, items: list, n: int = 5) -> list:
    scored = [(_score(query, it), it) for it in items]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for s, it in scored if s > 0][:n]


def search_issues(query: str, n: int = 5) -> list:
    return _rank(query, issues(), n)


def get_issue(number: int) -> dict | None:
    for it in issues():
        if it["number"] == number:
            return it
    return None


def search_pulls(query: str, n: int = 5) -> list:
    return _rank(query, pulls(), n)


def list_commits(n: int = 8) -> list:
    # already newest-first in the file
    return commits()[:n]


def search_notes(query: str, n: int = 5) -> list:
    return _rank(query, notes(), n)
