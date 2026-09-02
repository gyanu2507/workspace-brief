from workspace_brief.llm import maybe_rewrite


def test_no_key_is_a_noop(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert maybe_rewrite("q", "- Empty promo [#41]", ["#41"]) is None


def test_rewrite_dropped_if_it_loses_a_cite(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake")
    import httpx

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "All good, no citations."}}]}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    assert maybe_rewrite("q", "- Empty promo [#41]", ["#41"]) is None
