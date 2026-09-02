from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


def _csv(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name) or ""
    return tuple(x.strip() for x in raw.split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    env: str
    github_token: str | None
    github_timeout: float
    github_retries: int
    memory_path: Path
    trace_dir: Path
    log_level: str
    default_source: str
    default_repo: str | None
    api_host: str
    api_port: int
    api_key: str | None
    allowed_repos: frozenset[str]
    cors_origins: tuple[str, ...]
    rate_limit: int
    trust_proxy: bool

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def require_serve(self) -> None:
        """Refuse to bind an HTTP server that would be an open proxy."""
        if not self.is_production:
            return
        if not self.api_key:
            raise RuntimeError("BRIEF_API_KEY is required when BRIEF_ENV=production")
        if len(self.api_key) < 16:
            raise RuntimeError("BRIEF_API_KEY must be at least 16 characters in production")
        if self.default_source == "github" and not self.allowed_repos:
            raise RuntimeError(
                "BRIEF_ALLOWED_REPOS is required in production when BRIEF_SOURCE=github"
            )


def settings() -> Settings:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None
    api_key = os.environ.get("BRIEF_API_KEY") or None
    allowed = frozenset(x.lower() for x in _csv("BRIEF_ALLOWED_REPOS"))
    source = os.environ.get("BRIEF_SOURCE", "fixture")
    env = (os.environ.get("BRIEF_ENV") or "development").lower()
    if env not in ("development", "production", "test"):
        env = "development"
    return Settings(
        env=env,
        github_token=token,
        github_timeout=float(os.environ.get("BRIEF_GITHUB_TIMEOUT", "25")),
        github_retries=int(os.environ.get("BRIEF_GITHUB_RETRIES", "3")),
        memory_path=Path(os.environ.get("BRIEF_MEMORY_PATH", ".brief-memory.sqlite")),
        trace_dir=Path(os.environ.get("BRIEF_TRACE_DIR", "traces")),
        log_level=os.environ.get("BRIEF_LOG_LEVEL", "INFO").upper(),
        default_source=source,
        default_repo=os.environ.get("BRIEF_REPO") or None,
        api_host=os.environ.get("BRIEF_API_HOST", "0.0.0.0"),
        api_port=int(os.environ.get("BRIEF_API_PORT", "8000")),
        api_key=api_key,
        allowed_repos=allowed,
        cors_origins=_csv("BRIEF_CORS_ORIGINS"),
        rate_limit=int(os.environ.get("BRIEF_RATE_LIMIT", "60")),
        trust_proxy=os.environ.get("BRIEF_TRUST_PROXY", "").lower() in ("1", "true", "yes"),
    )


def setup_logging(level: str | None = None) -> None:
    logging.basicConfig(
        level=getattr(logging, (level or settings().log_level), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
