from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from workspace_brief.retrieve import rank

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


def search_issues(query: str, n: int = 5) -> list:
    return rank(query, issues(), n)


def get_issue(number: int) -> dict | None:
    for it in issues():
        if it["number"] == number:
            return it
    return None


def search_pulls(query: str, n: int = 5) -> list:
    return rank(query, pulls(), n)


def list_commits(n: int = 8) -> list:
    # already newest-first in the file
    return commits()[:n]


def search_notes(query: str, n: int = 5) -> list:
    return rank(query, notes(), n)


def get_note(note_id: str) -> dict | None:
    for it in notes():
        if it["id"] == note_id:
            return it
    return None
