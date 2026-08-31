from __future__ import annotations


def plan(question: str) -> dict:
    """Split a question into a rewrite + a few lookups.

    This is dumb on purpose. If GROQ/OPENAI is set the agent can replace
    it later; tests shouldn't need a key to get a sensible tool sequence.
    """
    q = " ".join(question.strip().split())
    low = q.lower()
    subs = [q]

    if any(w in low for w in ("changed", "change", "this quarter", "q3", "recent")):
        subs.append("recent commits merged pulls")
        subs.append("standup notes")

    if any(w in low for w in ("risk", "risks", "block", "blocked", "incident")):
        subs.append("open p0 p1 bugs")
        subs.append("incident webhook duplicate")

    if "promo" in low or "checkout" in low:
        subs.append("empty promo_code checkout")

    if "vat" in low or "eu" in low:
        subs.append("VAT EU legal vendor")

    # preserve order, drop dupes
    seen = set()
    out = []
    for s in subs:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)

    return {"rewrite": q, "subquestions": out[:5]}
