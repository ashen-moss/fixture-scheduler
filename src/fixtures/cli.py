"""Thin command-line wrapper around fixtures.generate_round_robin."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta

from fixtures import Fixture, generate_round_robin, schedule_fixtures


def _read_teams(path: str | None, inline: list[str]) -> list[str]:
    if path:
        with open(path, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return inline


def _read_venues(path: str) -> dict[str, str]:
    venues = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            team, venue = row[0].strip(), row[1].strip()
            venues[team] = venue
    return venues


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


def _format_text_dated(rounds: list[list[Fixture]]) -> str:
    lines = []
    for i, fixtures in enumerate(rounds, start=1):
        lines.append(f"Round {i}")
        for f in fixtures:
            lines.append(f"  {f.date.isoformat()}  {f.home} vs {f.away}  @ {f.venue}")
    return "\n".join(lines)


def _format_csv_dated(rounds: list[list[Fixture]]) -> str:
    lines = ["round,date,home,away,venue"]
    for i, fixtures in enumerate(rounds, start=1):
        for f in fixtures:
            lines.append(f"{i},{f.date.isoformat()},{f.home},{f.away},{f.venue}")
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
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="assign a date to each round, starting here and moving forward by --interval-days",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        default=7,
        help="days between rounds when --start-date is given (default: 7)",
    )
    parser.add_argument(
        "--venues-file",
        metavar="PATH",
        help="CSV of team,venue to override the default home-team venue (requires --start-date)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.venues_file and not args.start_date:
        parser.error("--venues-file requires --start-date")

    teams = _read_teams(args.from_file, args.teams)
    if len(teams) < 2:
        parser.error("need at least two teams")

    try:
        rounds = generate_round_robin(teams, double_round=args.double)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # unreachable, parser.error exits, but keeps type checkers happy

    if args.start_date:
        try:
            start = date.fromisoformat(args.start_date)
        except ValueError:
            parser.error(f"invalid --start-date: {args.start_date!r} (expected YYYY-MM-DD)")
            return 2  # unreachable, parser.error exits, but keeps type checkers happy

        venues = _read_venues(args.venues_file) if args.venues_file else None
        dated_rounds = schedule_fixtures(
            rounds, start, timedelta(days=args.interval_days), venues
        )
        formatter = _format_csv_dated if args.format == "csv" else _format_text_dated
        print(formatter(dated_rounds))
        return 0

    formatter = _format_csv if args.format == "csv" else _format_text
    print(formatter(rounds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
