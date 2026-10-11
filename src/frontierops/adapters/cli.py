"""FrontierOps command-line driving adapter."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from pydantic import ValidationError

from frontierops.build import run_build
from frontierops.config import config_service
from frontierops.identity import identity_service
from frontierops.sync import run_sync
from frontierops.rank import run_rank
from frontierops.brief import run_brief
from frontierops.review import run_review
from frontierops.render import run_render


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="frontier")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="validate config and initialize a run")
    build.add_argument("--config", type=Path, required=True)
    sync = commands.add_parser("sync", help="manually fetch source deltas")
    sync.add_argument("--config", type=Path, required=True)
    rank = commands.add_parser("rank", help="score and gate synchronized research signals")
    rank.add_argument("--run", type=Path, required=True)
    brief = commands.add_parser("brief", help="build a duration-aware briefing draft")
    brief.add_argument("--run", type=Path, required=True)
    review = commands.add_parser("review", help="validate and approve a briefing draft")
    review.add_argument("--run", type=Path, required=True)
    render = commands.add_parser("render", help="render an approved briefing")
    render.add_argument("--run", type=Path, required=True)

    schema = commands.add_parser("schema", help="print a JSON schema")
    schema_commands = schema.add_subparsers(dest="resource", required=True)
    schema_config = schema_commands.add_parser("config")
    schema_config.add_argument("--format", choices=["json"], default="json")

    config = commands.add_parser("config", help="manage validated configuration")
    actions = config.add_subparsers(dest="action", required=True)
    for name in ("inspect", "validate"):
        command = actions.add_parser(name)
        command.add_argument("--config", type=Path, default=Path("frontier.yaml"))
    diff = actions.add_parser("diff")
    diff.add_argument("--old", type=Path, required=True)
    diff.add_argument("--new", type=Path, required=True)
    draft = actions.add_parser("draft")
    draft.add_argument("--config", type=Path, default=Path("frontier.yaml"))
    draft.add_argument("--output", type=Path, required=True)
    apply = actions.add_parser("apply")
    apply.add_argument("--candidate", type=Path, required=True)
    apply.add_argument("--config", type=Path, default=Path("frontier.yaml"))

    scholar = commands.add_parser("scholar", help="resolve a stable scholar identity")
    scholar_resolve = scholar.add_subparsers(dest="action", required=True).add_parser("resolve")
    scholar_resolve.add_argument("--name", required=True)
    scholar_resolve.add_argument("--provider", default="semantic_scholar")
    venue = commands.add_parser("venue", help="resolve a stable venue identity")
    venue_resolve = venue.add_subparsers(dest="action", required=True).add_parser("resolve")
    venue_resolve.add_argument("--name", required=True)
    venue_resolve.add_argument("--year", type=int)
    venue_resolve.add_argument("--provider", default="openreview")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            print(run_build(args.config))
            return 0
        if args.command == "sync":
            print(run_sync(args.config))
            return 0
        if args.command == "rank":
            print(run_rank(args.run))
            return 0
        if args.command == "brief":
            print(run_brief(args.run))
            return 0
        if args.command == "review":
            print(run_review(args.run))
            return 0
        if args.command == "render":
            print(run_render(args.run))
            return 0
        if args.command in ("scholar", "venue"):
            identities = identity_service()
            candidates = (
                identities.resolve_scholar(args.name, args.provider)
                if args.command == "scholar"
                else identities.resolve_venue(args.name, args.year, args.provider)
            )
            payload = [candidate.model_dump(mode="json") for candidate in candidates]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        service = config_service()
        if args.command == "schema":
            print(json.dumps(service.schema(), indent=2, ensure_ascii=False))
        elif args.action == "inspect":
            print(json.dumps(service.inspect(args.config), indent=2, ensure_ascii=False))
        elif args.action == "validate":
            service.inspect(args.config)
            print(f"valid: {args.config}")
        elif args.action == "diff":
            changes = [asdict(change) for change in service.diff(args.old, args.new)]
            print(json.dumps(changes, indent=2, ensure_ascii=False))
        elif args.action == "draft":
            service.draft(args.config, args.output)
            print(args.output)
        elif args.action == "apply":
            service.apply(args.candidate, args.config)
            print(args.config)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"{args.command} failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
