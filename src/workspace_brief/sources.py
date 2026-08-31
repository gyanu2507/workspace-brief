from __future__ import annotations

from workspace_brief import fixture
from workspace_brief import github as gh


class FixtureSource:
    kind = "fixture"
    repo = "northstar"

    def search_issues(self, q, n=5):
        return fixture.search_issues(q, n)

    def get_issue(self, number):
        return fixture.get_issue(number)

    def search_pulls(self, q, n=5):
        return fixture.search_pulls(q, n)

    def list_commits(self, n=8):
        return fixture.list_commits(n)

    def search_notes(self, q, n=5):
        return fixture.search_notes(q, n)


class GithubSource:
    kind = "github"

    def __init__(self, repo: str):
        self.repo = repo

    def search_issues(self, q, n=5):
        return gh.search_issues(self.repo, q, n)

    def get_issue(self, number):
        return gh.get_issue(self.repo, number)

    def search_pulls(self, q, n=5):
        return gh.search_pulls(self.repo, q, n)

    def list_commits(self, n=8):
        return gh.list_commits(self.repo, n)

    def search_notes(self, q, n=5):
        return gh.search_notes(self.repo, q, n)


def get_source(kind: str, repo: str | None = None):
    if kind == "github":
        if not repo:
            raise ValueError("repo is required for github")
        return GithubSource(repo)
    return FixtureSource()
