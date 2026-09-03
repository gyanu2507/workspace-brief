from __future__ import annotations

import re

_ANAPHORA = re.compile(
    r"\b(that|this|those|these|it|them|same|the pr|the issue|the bug|the incident)\b",
    re.I,
)
_REMEMBER = ("remember that ", "remember ", "note that ")


def last_user_question(turns: list[dict] | None) -> str | None:
    for t in reversed(turns or []):
        if t.get("role") != "user":
            continue
        text = " ".join((t.get("text") or "").split())
        if not text:
            continue
        low = text.lower()
        if any(low.startswith(p) for p in _REMEMBER):
            continue
        return text
    return None


def expand_question(question: str, recent_turns: list[dict] | None = None) -> str:
    """Glue a short/anaphoric follow-up onto the last real question.

    Memory already stored the prior turn. The planner never looked at it,
    so "which PR treats that as missing" searched for "that" and missed #12.
    """
    q = " ".join(question.strip().split())
    prev = last_user_question(recent_turns)
    if not prev or prev.lower() == q.lower():
        return q
    if len(q.split()) <= 8 or _ANAPHORA.search(q):
        return f"{prev} {q}"
    return q


def plan(
    question: str,
    recent_turns: list[dict] | None = None,
    facts: list[str] | None = None,
) -> dict:
    """Split a question into a rewrite + a few lookups.

    Keyword extras are a fallback so tests do not need a model key.
    Follow-ups and remembered facts ride along as extra lookups.
    """
    q = expand_question(question, recent_turns)
    low = q.lower()
    subs = [q]

    if any(w in low for w in ("changed", "change", "this quarter", "q3", "recent", "landed")):
        subs.append("recent commits merged pulls")
        subs.append("standup notes")

    if any(w in low for w in ("risk", "risks", "block", "blocked", "incident")):
        subs.append("open p0 p1 bugs")
        subs.append("incident webhook duplicate")

    if "promo" in low or "checkout" in low:
        subs.append("empty promo_code checkout")

    if "vat" in low or "eu" in low:
        subs.append("VAT EU legal vendor")

    for fact in (facts or [])[:2]:
        fact = " ".join(fact.split())
        if fact:
            subs.append(fact)

    seen = set()
    out = []
    for s in subs:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)

    return {"rewrite": q, "subquestions": out[:5]}
