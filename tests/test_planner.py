from workspace_brief.planner import plan


def test_risk_question_adds_bug_lookup():
    p = plan("what are the main risks this quarter?")
    blob = " ".join(p["subquestions"]).lower()
    assert "p0" in blob or "incident" in blob


def test_keeps_original():
    q = "why is checkout 500ing"
    p = plan(q)
    assert p["rewrite"] == q
    assert p["subquestions"][0] == q
