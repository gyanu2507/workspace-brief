import httpx

from workspace_brief.github import GithubError, search_issues


class _Resp:
    def __init__(self, status, data=None, headers=None):
        self.status_code = status
        self.headers = headers or {}
        self._data = data if data is not None else []

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://api.github.com/"),
                response=httpx.Response(self.status_code),
            )


class _Client:
    def __init__(self, queue):
        self.queue = queue

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, path, params=None):
        return self.queue.pop(0)


def test_retries_on_503(monkeypatch):
    monkeypatch.setenv("BRIEF_GITHUB_RETRIES", "3")
    monkeypatch.setattr("workspace_brief.github.time.sleep", lambda *_: None)
    queue = [_Resp(503), _Resp(503), _Resp(200, [])]

    def factory(**kwargs):
        return _Client(queue)

    monkeypatch.setattr("workspace_brief.github.httpx.Client", factory)
    assert search_issues("acme/app", "crash") == []
    assert queue == []


def test_403_without_retry_after_fails_fast(monkeypatch):
    monkeypatch.setenv("BRIEF_GITHUB_RETRIES", "5")
    monkeypatch.setattr("workspace_brief.github.time.sleep", lambda *_: None)
    queue = [_Resp(403)]

    def factory(**kwargs):
        return _Client(queue)

    monkeypatch.setattr("workspace_brief.github.httpx.Client", factory)
    try:
        search_issues("acme/app", "crash")
        raise AssertionError("expected GithubError")
    except GithubError as e:
        assert "rate-limited" in str(e)
    assert queue == []


def test_bad_repo_shape():
    try:
        search_issues("noshape", "q")
        raise AssertionError("expected GithubError")
    except GithubError as e:
        assert "owner/name" in str(e)
