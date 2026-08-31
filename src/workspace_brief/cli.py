import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="brief",
        description="Question a GitHub repo (or a local fixture) about what changed.",
    )
    p.add_argument("question", nargs="?", help="plain-English question")
    p.add_argument(
        "--source",
        choices=("fixture", "github"),
        default="fixture",
        help="fixture is offline; github hits the public API",
    )
    p.add_argument("--repo", help="owner/name, only used with --source github")
    p.add_argument(
        "--session",
        default="default",
        help="memory session id, so follow-ups can stick",
    )
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.question:
        build_parser().print_help()
        return 1
    if args.source == "github" and not args.repo:
        print("brief: --repo owner/name is required with --source github", file=sys.stderr)
        return 2
    print(f"[{args.source}] {args.question}")
    print("(agent not hooked up)")
    return 0
