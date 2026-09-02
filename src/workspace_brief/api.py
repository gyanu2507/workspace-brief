from __future__ import annotations

import hmac
import logging
import sqlite3
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from workspace_brief import __version__
from workspace_brief.agent import run
from workspace_brief.config import settings, setup_logging
from workspace_brief.github import GithubError, RepoNotAllowed
from workspace_brief.trace import write_trace

setup_logging()
log = logging.getLogger("workspace_brief.api")


class _RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            xs = [t for t in self._hits[key] if now - t < window]
            if len(xs) >= limit:
                self._hits[key] = xs
                return False
            xs.append(now)
            self._hits[key] = xs
            return True


limiter = _RateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = settings()
    cfg.require_serve()
    log.info(
        "listening env=%s source=%s version=%s",
        cfg.env,
        cfg.default_source,
        __version__,
    )
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="workspace-brief",
        version=__version__,
        description="Ask a live GitHub workspace what changed. Answers cite retrieved records only.",
        lifespan=lifespan,
    )
    origins = list(settings().cors_origins)
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-Id"],
        )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return application


app = create_app()


class BriefIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    source: Literal["fixture", "github"] | None = None
    repo: str | None = Field(default=None, max_length=200)
    session: str = Field(default="default", pattern=r"^[A-Za-z0-9._-]{1,80}$")


class BriefOut(BaseModel):
    answer: str
    citations: list[str]
    source: str
    repo: str | None
    trace: str


def _client_key(request: Request) -> str:
    cfg = settings()
    if cfg.trust_proxy:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded:
            return forwarded
    if request.client:
        return request.client.host
    return "unknown"


def _require_key(request: Request) -> None:
    key = settings().api_key
    if not key:
        return
    got = (request.headers.get("x-api-key") or "").strip()
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        got = auth[7:].strip()
    if not got or len(got) != len(key) or not hmac.compare_digest(got, key):
        raise HTTPException(status_code=401, detail="missing or invalid api key")


def _gate(request: Request) -> None:
    _require_key(request)
    if not limiter.allow(_client_key(request), settings().rate_limit):
        raise HTTPException(
            status_code=429,
            detail="rate limited",
            headers={"Retry-After": "60"},
        )


@app.get("/")
def root():
    return {
        "name": "workspace-brief",
        "version": __version__,
        "health": "/health",
        "ready": "/ready",
        "docs": "/docs",
        "brief": "POST /brief",
    }


@app.get("/health")
def health():
    cfg = settings()
    return {"ok": True, "source": cfg.default_source, "version": __version__}


@app.get("/ready")
def ready():
    cfg = settings()
    try:
        cfg.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(cfg.memory_path), timeout=2) as conn:
            conn.execute("select 1")
    except sqlite3.Error:
        log.exception("readiness: memory store")
        raise HTTPException(status_code=503, detail="memory store unavailable") from None
    return {"ok": True, "memory": "ok", "version": __version__}


@app.post("/brief", response_model=BriefOut)
def brief(body: BriefIn, request: Request):
    _gate(request)
    cfg = settings()
    source = body.source or (
        cfg.default_source if cfg.default_source in ("fixture", "github") else "fixture"
    )
    repo = body.repo or cfg.default_repo
    if source == "github" and not repo:
        raise HTTPException(status_code=400, detail="repo is required with source=github")
    if source == "github" and cfg.allowed_repos and repo.lower() not in cfg.allowed_repos:
        raise HTTPException(status_code=403, detail=f"repo not allowed: {repo}")
    try:
        result = run(
            body.question,
            source=source,
            repo=repo,
            session=body.session,
        )
    except RepoNotAllowed as e:
        raise HTTPException(status_code=403, detail=str(e)) from None
    except GithubError as e:
        log.warning("github: %s", e)
        detail = "github upstream error" if cfg.is_production else str(e)
        raise HTTPException(status_code=502, detail=detail) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    path = write_trace(result, cfg.trace_dir)
    return BriefOut(
        answer=result["answer"],
        citations=result["citations"],
        source=result["source"],
        repo=result.get("repo"),
        trace=path.name,
    )


def serve() -> None:
    import uvicorn

    cfg = settings()
    cfg.require_serve()
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port, proxy_headers=cfg.trust_proxy)


if __name__ == "__main__":
    serve()
