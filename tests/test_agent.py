import json
from pathlib import Path

from workspace_brief.agent import run
from workspace_brief.trace import write_trace

GOLD = json.loads(
    (Path(__file__).resolve().parents[1] / "evals" / "gold.json").read_text()
)


def _cited(result: dict) -> set[str]:
    found = set(result["citations"])
    for ev in result["evidence"]:
        if "number" in ev:
            found.add(f"#{ev['number']}")
        if ev.get("id"):
            found.add(ev["id"])
        if ev.get("sha"):
            found.add(ev["sha"])
    return found


def test_gold_hit_rate(tmp_path):
    db = tmp_path / "mem.sqlite"
    hits = 0
    missed = []
    for row in GOLD:
        r = run(row["q"], session="eval", memory_path=db)
        got = _cited(r)
        need = set(row["must_cite"])
        if need <= got:
            hits += 1
        else:
            missed.append((row["q"], sorted(need - got)))
    rate = hits / len(GOLD)
    # keep this visible in pytest -s
    print(f"hit rate {hits}/{len(GOLD)} = {rate:.0%}")
    assert rate >= 0.75, missed


def test_remember_roundtrip(tmp_path):
    db = tmp_path / "mem.sqlite"
    run("remember that northstar is the priority", session="a", memory_path=db)
    r = run("what are the risks?", session="a", memory_path=db)
    assert any("northstar is the priority" in f for f in r["memory_used"])


def test_trace_has_path(tmp_path):
    r = run("promo 500", memory_path=tmp_path / "m.sqlite")
    p = write_trace(r, tmp_path)
    data = json.loads(p.read_text())
    assert data["question"] == "promo 500"
    assert data["citations"]
    assert data["tool_calls"]


def test_followup_retrieves_the_promo_pr(tmp_path):
    db = tmp_path / "mem.sqlite"
    run("why is checkout returning 500", session="s", memory_path=db)
    r = run("which PR treats that as missing", session="s", memory_path=db)
    found = _cited(r)
    assert "#12" in found
    assert "checkout" in r["rewrite"].lower()
