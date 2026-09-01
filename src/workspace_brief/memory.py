from __future__ import annotations

import sqlite3
from pathlib import Path

from workspace_brief.config import settings


def _conn(path: Path | None = None) -> sqlite3.Connection:
    p = path or settings().memory_path
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        create table if not exists turns (
            id integer primary key,
            session text not null,
            role text not null,
            text text not null,
            ts datetime default current_timestamp
        );
        create table if not exists facts (
            id integer primary key,
            session text not null,
            fact text not null,
            ts datetime default current_timestamp,
            unique(session, fact)
        );
        """
    )
    return c


def add_turn(session: str, role: str, text: str, path: Path | None = None) -> None:
    with _conn(path) as c:
        c.execute(
            "insert into turns(session, role, text) values (?,?,?)",
            (session, role, text),
        )


def recent_turns(session: str, n: int = 6, path: Path | None = None) -> list[dict]:
    with _conn(path) as c:
        rows = c.execute(
            "select role, text, ts from turns where session=? order by id desc limit ?",
            (session, n),
        ).fetchall()
    rows = list(rows)
    rows.reverse()
    return [dict(r) for r in rows]


def remember(session: str, fact: str, path: Path | None = None) -> bool:
    fact = fact.strip()
    if not fact:
        return False
    with _conn(path) as c:
        try:
            c.execute(
                "insert into facts(session, fact) values (?,?)",
                (session, fact),
            )
        except sqlite3.IntegrityError:
            return False
    return True


def facts(session: str, path: Path | None = None) -> list[str]:
    with _conn(path) as c:
        rows = c.execute(
            "select fact from facts where session=? order by id",
            (session,),
        ).fetchall()
    return [r["fact"] for r in rows]


def forget(session: str, fact: str, path: Path | None = None) -> None:
    with _conn(path) as c:
        c.execute(
            "delete from facts where session=? and fact=?",
            (session, fact),
        )
