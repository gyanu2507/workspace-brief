from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def blob(item: dict) -> str:
    parts = [str(v) for v in item.values() if v is not None]
    return " ".join(parts)


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs = docs
        n = len(docs) or 1
        self.avgdl = sum(len(d) for d in docs) / n
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {
            t: math.log((n - f + 0.5) / (f + 0.5) + 1.0) for t, f in df.items()
        }

    def score(self, query: list[str], i: int) -> float:
        d = self.docs[i]
        if not d:
            return 0.0
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for t in query:
            freq = tf.get(t)
            if not freq:
                continue
            idf = self.idf.get(t, 0.0)
            s += idf * (freq * (self.k1 + 1)) / (
                freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            )
        return s


def rank(query: str, items: list, n: int = 5) -> list:
    """Score items against query. Zero-overlap rows stay out."""
    q = tokens(query)
    if not q or not items:
        return []
    docs = [tokens(blob(it)) for it in items]
    bm = BM25(docs)
    scored = [(bm.score(q, i), it) for i, it in enumerate(items)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for s, it in scored if s > 0][:n]
