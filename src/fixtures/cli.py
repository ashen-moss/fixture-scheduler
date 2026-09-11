"""Thin command-line wrapper around fixtures.generate_round_robin."""

from __future__ import annotations

import argparse
import sys

from fixtures import generate_round_robin


def _read_teams(path: str | None, inline: list[str]) -> list[str]:
    if path:
        with open(path, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return inline


def _format_text(rounds: list[list[tuple[str, str]]]) -> str:
    lines = []
    for i, matches in enumerate(rounds, start=1):
        lines.append(f"Round {i}")
        for home, away in matches:
            lines.append(f"  {home} vs {away}")
    return "\n".join(lines)


def _format_csv(rounds: list[list[tuple[str, str]]]) -> str:
    lines = ["round,home,away"]
    for i, matches in enumerate(rounds, start=1):
        for home, away in matches:
            lines.append(f"{i},{home},{away}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fixtures",
        description="Generate a round-robin fixture schedule.",
    )
    parser.add_argument(
        "teams",
        nargs="*",
        help="team names, in the order they should be seeded",
    )
    parser.add_argument(
        "--from-file",
        metavar="PATH",
        help="read team names from a file, one per line (overrides positional args)",
    )
    parser.add_argument(
        "--double",
        action="store_true",
        help="generate a home-and-away double round-robin",
    )
    parser.add_argument(
        "--format",
        choices=("text", "csv"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    teams = _read_teams(args.from_file, args.teams)
    if len(teams) < 2:
        parser.error("need at least two teams")

    try:
        rounds = generate_round_robin(teams, double_round=args.double)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # unreachable, parser.error exits, but keeps type checkers happy

    formatter = _format_csv if args.format == "csv" else _format_text
    print(formatter(rounds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
