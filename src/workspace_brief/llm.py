from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

GROQ = "https://api.groq.com/openai/v1/chat/completions"
OPENAI = "https://api.openai.com/v1/chat/completions"


def maybe_rewrite(question: str, extractive: str, cites: list[str]) -> str | None:
    """Optional prose pass. Must keep the citation tokens we already chose."""
    groq = os.environ.get("GROQ_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")
    base = (os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    if groq:
        url, key, model = GROQ, groq, os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    elif openai and base:
        # OpenAI-compatible hosts (e.g. Groq) put the key in OPENAI_API_KEY.
        url = f"{base}/chat/completions"
        key, model = openai, os.environ.get("OPENAI_MODEL", "openai/gpt-oss-20b")
    elif openai:
        url, key, model = OPENAI, openai, os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    else:
        return None

    system = (
        "Rewrite the extractive bullets as a short brief. "
        "Do not add facts. Keep every citation token like #41 or a1c3e02 "
        "exactly as written. If you cannot, return the original bullets."
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Question: {question}\n\n{extractive}",
            },
        ],
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        import httpx

        with httpx.Client(timeout=20) as c:
            r = c.post(url, json=payload, headers=headers)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("rewrite failed: %s", e)
        return None
    if not text:
        return None
    for c in cites:
        if c not in text:
            return None
    return text
