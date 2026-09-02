from workspace_brief.redact import redact, redact_obj
from workspace_brief.trace import write_trace


def test_redact_bearer():
    assert redact("Authorization: Bearer ghp_abcdefghijklmnopqrstuvwxyz") == "Authorization: Bearer ***"


def test_redact_github_pat():
    out = redact("token ghp_abcdefghijklmnopqrstuvwxyz1234 leftover")
    assert "ghp_" not in out
    assert "***" in out


def test_redact_openai_and_groq():
    text = "sk-abcdefghijklmnopqrstuvwxyz123456 gsk_abcdefghijklmnopqrstuvwxyz123456"
    out = redact(text)
    assert "sk-" not in out
    assert "gsk_" not in out


def test_redact_obj_nested():
    got = redact_obj({"err": "Bearer secret-token-value", "n": 1, "xs": ["ghp_abcdefghijklmnopqrstuvwxyz"]})
    assert "secret-token-value" not in got["err"]
    assert got["n"] == 1
    assert "ghp_" not in got["xs"][0]


def test_trace_redacts_tokens(tmp_path):
    path = write_trace(
        {"answer": "call with ghp_abcdefghijklmnopqrstuvwxyz1234", "citations": []},
        tmp_path,
    )
    text = path.read_text()
    assert "ghp_" not in text
    assert "***" in text


def test_trace_names_are_unique(tmp_path):
    a = write_trace({"answer": "one", "citations": []}, tmp_path)
    b = write_trace({"answer": "two", "citations": []}, tmp_path)
    assert a != b
    assert a.name != b.name
