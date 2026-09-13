"""§7 CLI: amp render --catalog catalog.json messages.jsonl"""
import argparse
import json
import sys
from typing import Iterable

from .catalog import Catalog
from .errors import AmpError
from .render import render_message


def _iter_lines(path: str) -> Iterable[str]:
    if path == "-":
        yield from sys.stdin
    else:
        with open(path, encoding="utf-8") as f:
            yield from f


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="amp")
    sub = parser.add_subparsers(dest="command", required=True)

    render_cmd = sub.add_parser("render")
    render_cmd.add_argument("--catalog", required=True)
    render_cmd.add_argument("messages")
    render_cmd.add_argument("--skip-errors", action="store_true")

    args = parser.parse_args(argv)
    catalog = Catalog.load(args.catalog)
    had_error = False

    for line in _iter_lines(args.messages):
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        try:
            print(render_message(message, catalog))
        except AmpError as e:
            had_error = True
            print(f"{e.kind}: {e}", file=sys.stderr)
            if not args.skip_errors:
                return 1

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
