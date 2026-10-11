"""FrontierOps command-line entry point."""

import argparse
from pathlib import Path
import sys

from pydantic import ValidationError

from frontierops.build import run_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="frontier")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="validate config and initialize a run")
    build.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        run_dir = run_build(args.config)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 2
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
