from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
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


def settings() -> Settings:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None
    return Settings(
        github_token=token,
        github_timeout=float(os.environ.get("BRIEF_GITHUB_TIMEOUT", "25")),
        github_retries=int(os.environ.get("BRIEF_GITHUB_RETRIES", "3")),
        memory_path=Path(os.environ.get("BRIEF_MEMORY_PATH", ".brief-memory.sqlite")),
        trace_dir=Path(os.environ.get("BRIEF_TRACE_DIR", "traces")),
        log_level=os.environ.get("BRIEF_LOG_LEVEL", "INFO").upper(),
        default_source=os.environ.get("BRIEF_SOURCE", "fixture"),
        default_repo=os.environ.get("BRIEF_REPO") or None,
        api_host=os.environ.get("BRIEF_API_HOST", "0.0.0.0"),
        api_port=int(os.environ.get("BRIEF_API_PORT", "8000")),
    )


def setup_logging(level: str | None = None) -> None:
    logging.basicConfig(
        level=getattr(logging, (level or settings().log_level), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
