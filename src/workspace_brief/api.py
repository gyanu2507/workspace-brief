from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from workspace_brief.agent import run
from workspace_brief.config import settings, setup_logging
from workspace_brief.github import GithubError
from workspace_brief.trace import write_trace

setup_logging()
log = logging.getLogger("workspace_brief.api")

app = FastAPI(
    title="workspace-brief",
    version="0.2.0",
    description="Ask a live GitHub workspace what changed. Citations only.",
)


class BriefIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    source: Literal["fixture", "github"] = "fixture"
    repo: str | None = None
    session: str = Field(default="default", max_length=80)


class BriefOut(BaseModel):
    answer: str
    citations: list[str]
    source: str
    repo: str | None
    trace: str


@app.get("/health")
def health():
    return {"ok": True, "source": settings().default_source}


@app.post("/brief", response_model=BriefOut)
def brief(body: BriefIn):
    if body.source == "github" and not body.repo:
        raise HTTPException(status_code=400, detail="repo is required with source=github")
    try:
        result = run(
            body.question,
            source=body.source,
            repo=body.repo,
            session=body.session,
        )
    except GithubError as e:
        log.warning("github: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    path = write_trace(result, settings().trace_dir)
    return BriefOut(
        answer=result["answer"],
        citations=result["citations"],
        source=result["source"],
        repo=result.get("repo"),
        trace=str(path),
    )


def serve() -> None:
    import uvicorn

    cfg = settings()
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port)


if __name__ == "__main__":
    serve()
