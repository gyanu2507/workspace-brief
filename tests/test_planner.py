from workspace_brief.planner import expand_question, plan


def test_risk_question_adds_bug_lookup():
    p = plan("what are the main risks this quarter?")
    blob = " ".join(p["subquestions"]).lower()
    assert "p0" in blob or "incident" in blob


def test_keeps_original():
    q = "why is checkout 500ing"
    p = plan(q)
    assert p["rewrite"] == q
    assert p["subquestions"][0] == q


def test_followup_glues_last_question():
    turns = [{"role": "user", "text": "why is checkout returning 500"}]
    q = "which PR treats that as missing"
    assert "checkout" in expand_question(q, turns).lower()
    p = plan(q, recent_turns=turns)
    assert "checkout" in p["rewrite"].lower()
    assert p["subquestions"][0] == p["rewrite"]
