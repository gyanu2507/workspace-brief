from __future__ import annotations

from workspace_brief.planner import plan
from workspace_brief.sources import get_source
from workspace_brief import memory as mem

MAX_CALLS = 8


def _cite(item: dict) -> str:
    if "sha" in item:
        return item["sha"]
    if "number" in item:
        return f"#{item['number']}"
    return item.get("id") or "?"


def _key(item: dict) -> str:
    if "sha" in item:
        return f"commit:{item['sha']}"
    if "number" in item:
        return f"n:{item['number']}:{item.get('title', '')[:20]}"
    return f"id:{item.get('id')}"


def _label(item: dict) -> str:
    return item.get("title") or item.get("message") or item.get("id") or _cite(item)


def synthesize(question: str, evidence: list[dict]) -> tuple[str, list[str]]:
    if not evidence:
        return (
            "Nothing in the workspace matched that. Either it isn't in the "
            "issues/PRs/notes, or the lookup was too narrow.",
            [],
        )

    cites = []
    lines = []
    for ev in evidence[:8]:
        c = _cite(ev)
        if c not in cites:
            cites.append(c)
        extra = ""
        if ev.get("state"):
            extra = f" ({ev['state']})"
        lines.append(f"- {_label(ev)}{extra} [{c}]")

    answer = (
        f"Based on the workspace, here's what I can ground for: {question}\n\n"
        + "\n".join(lines)
        + "\n\nI only used the records above — if something's missing it wasn't retrieved."
    )
    return answer, cites


def _maybe_remember(question: str, session: str, path) -> str | None:
    raw = question.strip()
    low = raw.lower()
    for prefix in ("remember that ", "remember ", "note that "):
        if low.startswith(prefix):
            fact = raw[len(prefix) :].strip()
            if mem.remember(session, fact, path):
                return fact
            return fact
    return None


def run(
    question: str,
    source: str = "fixture",
    repo: str | None = None,
    session: str = "default",
    memory_path=None,
) -> dict:
    written = _maybe_remember(question, session, memory_path)
    known = mem.facts(session, memory_path)
    recent = mem.recent_turns(session, path=memory_path)

    src = get_source(source, repo)
    planned = plan(question)

    evidence = []
    seen = set()
    calls = []

    tools = [
        ("search_issues", src.search_issues),
        ("search_pulls", src.search_pulls),
        ("search_notes", src.search_notes),
    ]

    for sq in planned["subquestions"]:
        for name, fn in tools:
            if len(calls) >= MAX_CALLS:
                break
            try:
                hits = fn(sq)
            except Exception as e:
                calls.append({"tool": name, "query": sq, "error": str(e), "hits": 0})
                continue
            calls.append({"tool": name, "query": sq, "hits": len(hits)})
            for h in hits:
                k = _key(h)
                if k in seen:
                    continue
                seen.add(k)
                evidence.append(h)
        if len(calls) >= MAX_CALLS:
            break

    # always grab recent commits once; cheap and answers "what changed"
    if len(calls) < MAX_CALLS:
        try:
            commits = src.list_commits()
            calls.append({"tool": "list_commits", "query": None, "hits": len(commits)})
            for h in commits:
                k = _key(h)
                if k not in seen:
                    seen.add(k)
                    evidence.append(h)
        except Exception as e:
            calls.append({"tool": "list_commits", "query": None, "error": str(e), "hits": 0})

    answer, cites = synthesize(question, evidence)
    if known:
        answer += "\n\nUsing long-term notes: " + "; ".join(known)

    mem.add_turn(session, "user", question, memory_path)
    mem.add_turn(session, "assistant", answer, memory_path)

    return {
        "question": question,
        "rewrite": planned["rewrite"],
        "subquestions": planned["subquestions"],
        "tool_calls": calls,
        "evidence": evidence,
        "citations": cites,
        "answer": answer,
        "source": src.kind,
        "repo": src.repo,
        "memory_used": known,
        "memory_written": [written] if written else [],
        "recent_turns": len(recent),
    }
