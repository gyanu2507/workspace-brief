import argparse
import logging
import sys
from pathlib import Path

from workspace_brief.agent import run
from workspace_brief.config import settings, setup_logging
from workspace_brief.github import GithubError
from workspace_brief.trace import write_trace

log = logging.getLogger("workspace_brief")


def build_parser() -> argparse.ArgumentParser:
    cfg = settings()
    p = argparse.ArgumentParser(
        prog="brief",
        description="Question a GitHub repo (or a local fixture) about what changed.",
    )
    p.add_argument("question", nargs="?", help="plain-English question")
    p.add_argument(
        "--source",
        choices=("fixture", "github"),
        default=cfg.default_source if cfg.default_source in ("fixture", "github") else "fixture",
        help="fixture is offline; github hits the public API",
    )
    p.add_argument("--repo", default=cfg.default_repo, help="owner/name, only used with --source github")
    p.add_argument(
        "--session",
        default="default",
        help="memory session id, so follow-ups can stick",
    )
    p.add_argument(
        "--trace-dir",
        default=str(cfg.trace_dir),
        help="where to write the json trace for this run",
    )
    return p


def main(argv=None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    if not args.question:
        build_parser().print_help()
        return 1
    if args.source == "github" and not args.repo:
        print("brief: --repo owner/name is required with --source github", file=sys.stderr)
        return 2

    try:
        result = run(
            args.question,
            source=args.source,
            repo=args.repo,
            session=args.session,
        )
    except GithubError as e:
        log.error("%s", e)
        print(f"brief: {e}", file=sys.stderr)
        return 3
    path = write_trace(result, Path(args.trace_dir))
    print(result["answer"])
    print(f"\ntrace: {path}", file=sys.stderr)
    return 0
