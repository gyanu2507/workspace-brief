from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

TRACE_DIR = Path("traces")


def _snip(ev: dict) -> dict:
    body = ev.get("body") or ev.get("message") or ""
    out = {}
    for k in ("number", "title", "state", "sha", "id", "updated", "url", "author"):
        if ev.get(k) not in (None, "", []):
            out[k] = ev[k]
    if body:
        out["snippet"] = body.strip().replace("\n", " ")[:240]
    return out


def write_trace(result: dict, directory: Path | None = None) -> Path:
    d = directory or TRACE_DIR
    d.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = d / f"{name}.json"
    payload = {
        "question": result.get("question"),
        "rewrite": result.get("rewrite"),
        "subquestions": result.get("subquestions"),
        "tool_calls": result.get("tool_calls"),
        "evidence": [_snip(ev) for ev in result.get("evidence") or []],
        "memory_used": result.get("memory_used"),
        "memory_written": result.get("memory_written"),
        "citations": result.get("citations"),
        "answer": result.get("answer"),
        "source": result.get("source"),
        "repo": result.get("repo"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path
