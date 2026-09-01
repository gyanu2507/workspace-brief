from __future__ import annotations

import re

_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)\S+"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghu_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
)


def redact(text: str) -> str:
    out = text
    for pat in _PATTERNS:
        out = pat.sub(lambda m: (m.group(1) + "***") if m.lastindex else "***", out)
    return out


def redact_obj(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    return value
