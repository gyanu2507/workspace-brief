from __future__ import annotations

import logging
import re

from workspace_brief import memory as mem
from workspace_brief.planner import plan
from workspace_brief.redact import redact
from workspace_brief.retrieve import rank
from workspace_brief.sources import get_source

log = logging.getLogger(__name__)

MAX_CALLS = 8
MAX_EVIDENCE = 8

# retrieved text is data. if it tries to drive the model, drop the body.
_INJECT = re.compile(
    r"ignore (all )?(previous|prior) instructions"
    r"|you are now"
    r"|system\s*:"
    r"|do not cite",
    re.I,
)


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
        return f"n:{item['number']}"
    return f"id:{item.get('id')}"


def _label(item: dict) -> str:
    return item.get("title") or item.get("message") or item.get("id") or _cite(item)


def _snippet(item: dict) -> str | None:
    body = (item.get("body") or item.get("message") or "").strip()
    if not body:
        return None
    if _INJECT.search(body):
        return None
    line = body.split("\n", 1)[0].strip()
    return line[:180] if line else None


def _wants_commits(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in ("changed", "change", "landed", "recent", "commit", "this quarter", "q3"))


def _lookups(sq: str, src) -> list:
    # issues/PRs/notes every time; commits are gated separately because
    # dumping the whole log into every answer was drowning the signal.
    return [
        ("search_issues", lambda q=sq: src.search_issues(q)),
        ("search_pulls", lambda q=sq: src.search_pulls(q)),
        ("search_notes", lambda q=sq: src.search_notes(q)),
    ]


_KIND_ORDER = ("Issues", "Pull requests", "Notes", "Commits")


def _kind(item: dict) -> str:
    if item.get("sha"):
        return "Commits"
    if item.get("id"):
        return "Notes"
    if "labels" in item:
        return "Issues"
    return "Pull requests"


def synthesize(question: str, evidence: list[dict]) -> tuple[str, list[str]]:
    if not evidence:
        return (
            "Nothing in the workspace matched that. Either it isn't in the "
            "issues/PRs/notes, or the lookup was too narrow.",
            [],
        )

    cites = []
    groups: dict[str, list[str]] = {k: [] for k in _KIND_ORDER}
    for ev in evidence:
        c = _cite(ev)
        if c not in cites:
            cites.append(c)
        extra = f" ({ev['state']})" if ev.get("state") else ""
        snip = _snippet(ev)
        line = f"- {_label(ev)}{extra} [{c}]"
        if snip:
            line += f": {snip}"
        groups[_kind(ev)].append(line)

    used = [k for k in _KIND_ORDER if groups[k]]
    parts = []
    for kind in used:
        if len(used) > 1:
            parts.append(kind)
        parts.extend(groups[kind])
    return "\n".join(parts), cites


def _maybe_remember(question: str, session: str, path) -> str | None:
    raw = question.strip()
    low = raw.lower()
    for prefix in ("remember that ", "remember ", "note that "):
        if low.startswith(prefix):
            fact = raw[len(prefix) :].strip()
            if fact:
                mem.remember(session, fact, path)
            return fact
    return None


def _collect(src, question: str, subquestions: list[str]) -> tuple[list[dict], list[dict]]:
    evidence = []
    seen = set()
    calls = []

    def add_hits(name, query, hits):
        calls.append({"tool": name, "query": query, "hits": len(hits)})
        for h in hits:
            k = _key(h)
            if k in seen:
                continue
            seen.add(k)
            evidence.append(h)

    if _wants_commits(question):
        try:
            commits = src.list_commits()
            add_hits("list_commits", None, commits)
        except Exception as e:
            calls.append({"tool": "list_commits", "query": None, "error": redact(str(e)), "hits": 0})

    for sq in subquestions:
        for name, fn in _lookups(sq, src):
            if len(calls) >= MAX_CALLS:
                break
            try:
                hits = fn()
            except Exception as e:
                calls.append({"tool": name, "query": sq, "error": redact(str(e)), "hits": 0})
                continue
            add_hits(name, sq, hits)
        if len(calls) >= MAX_CALLS:
            break

    # pull the full issue/note once we have an id — search snippets are short
    for ev in list(evidence):
        if len(calls) >= MAX_CALLS:
            break
        if ev.get("number") and not (ev.get("body") or "").strip():
            try:
                full = src.get_issue(ev["number"])
            except Exception as e:
                calls.append({"tool": "get_issue", "query": ev["number"], "error": redact(str(e)), "hits": 0})
                continue
            calls.append({"tool": "get_issue", "query": ev["number"], "hits": 1 if full else 0})
            if full:
                evidence[evidence.index(ev)] = full
        elif ev.get("id") and hasattr(src, "get_note"):
            try:
                full = src.get_note(ev["id"])
            except Exception as e:
                calls.append({"tool": "get_note", "query": ev["id"], "error": redact(str(e)), "hits": 0})
                continue
            if full:
                calls.append({"tool": "get_note", "query": ev["id"], "hits": 1})
                evidence[evidence.index(ev)] = full

    return evidence, calls


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
    planned = plan(question, recent_turns=recent, facts=known)
    raw, calls = _collect(src, planned["rewrite"], planned["subquestions"])

    rank_q = planned["rewrite"]
    if known:
        rank_q = rank_q + " " + " ".join(known)
    evidence = rank(rank_q, raw, n=MAX_EVIDENCE) or raw[:MAX_EVIDENCE]
    answer, cites = synthesize(question, evidence)
    try:
        from workspace_brief.llm import maybe_rewrite

        rewritten = maybe_rewrite(question, answer, cites)
        if rewritten:
            answer = rewritten
    except Exception:
        log.exception("llm rewrite skipped")

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
