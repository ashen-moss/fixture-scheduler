"""Round-robin sports fixture scheduling.

The core algorithm is the standard "circle method": hold one team fixed,
rotate the rest around it once per round. With an odd number of teams a
placeholder bye slot is added so the rotation still works, then dropped
from the output. Once the pairings are fixed, home/away is assigned in a
separate pass that balances each team's run of consecutive home or away
games rather than following raw rotation position.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

Match = tuple[str, str]
Round = list[Match]

_BYE = object()  # sentinel; never equal to a real team name, never printed


def generate_round_robin(teams: list[str], double_round: bool = False) -> list[Round]:
    """Return a full round-robin schedule as a list of rounds.

    Each round is a list of (home, away) pairs. With fewer than two teams
    there is nothing to schedule and an empty list is returned.

    Home/away within each pairing is assigned to avoid consecutive home
    or away runs: a team coming off a home game is preferred for the away
    slot in its next fixture, and vice versa. See _assign_home_away.

    Raises ValueError on duplicate team names, since a duplicate would
    otherwise silently play itself.
    """
    if len(set(teams)) != len(teams):
        raise ValueError("duplicate team names")
    if len(teams) < 2:
        return []

    slots: list[object] = list(teams)
    if len(slots) % 2 == 1:
        slots.append(_BYE)

    n = len(slots)
    num_rounds = n - 1
    fixed = slots[0]
    rotating = slots[1:]

    raw_rounds: list[list[tuple[str, str]]] = []
    for _ in range(num_rounds):
        arranged = [fixed] + rotating
        pairs: list[tuple[str, str]] = []
        for i in range(n // 2):
            a, b = arranged[i], arranged[n - 1 - i]
            if a is not _BYE and b is not _BYE:
                pairs.append((a, b))
        raw_rounds.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]

    rounds = _assign_home_away(raw_rounds, teams)

    if double_round:
        return_leg = [[(away, home) for home, away in rnd] for rnd in rounds]
        rounds = rounds + return_leg

    return rounds


def _assign_home_away(raw_rounds: list[list[tuple[str, str]]], teams: list[str]) -> list[Round]:
    """Turn undirected pairings into (home, away) fixtures, balancing venues.

    `streak` tracks each team's current run: positive means N consecutive
    home games, negative means N consecutive away games. Whichever team in
    a pairing is more overdue for a change gets it. If both are equally
    overdue for the same change, the one with the longer run wins it and
    the other's run is extended by one instead - one of them has to stay
    put, and it should be the team that has less riding on it.
    """
    streak = {team: 0 for team in teams}
    rounds: list[Round] = []
    for pairs in raw_rounds:
        fixtures: Round = []
        for a, b in pairs:
            a_due_away = streak[a] > 0
            b_due_away = streak[b] > 0
            if a_due_away and not b_due_away:
                home, away = b, a
            elif b_due_away and not a_due_away:
                home, away = a, b
            elif a_due_away and b_due_away:
                home, away = (b, a) if streak[a] >= streak[b] else (a, b)
            else:
                home, away = (a, b) if streak[a] <= streak[b] else (b, a)
            fixtures.append((home, away))
            streak[home] = streak[home] + 1 if streak[home] > 0 else 1
            streak[away] = streak[away] - 1 if streak[away] < 0 else -1
        rounds.append(fixtures)
    return rounds


@dataclass(frozen=True)
class Fixture:
    """A single scheduled match: who, where, and when."""

    home: str
    away: str
    date: date
    venue: str


def schedule_fixtures(
    rounds: list[Round],
    start_date: date,
    interval: timedelta = timedelta(weeks=1),
    venues: dict[str, str] | None = None,
) -> list[list[Fixture]]:
    """Attach a date and venue to every match in a round-robin schedule.

    Rounds are played `interval` apart starting on `start_date`, with every
    match in a round sharing that round's date - a real league might spread
    a round across a weekend, but that's a presentation detail callers can
    layer on top rather than something the scheduler should guess at.

    Venue defaults to the home team's name, since a fixture is normally
    played at the home side's ground; pass `venues` (team name -> venue
    name) to override that for teams that play elsewhere.
    """
    venues = venues or {}
    scheduled: list[list[Fixture]] = []
    for i, matches in enumerate(rounds):
        round_date = start_date + interval * i
        scheduled.append(
            [
                Fixture(home=home, away=away, date=round_date, venue=venues.get(home, home))
                for home, away in matches
            ]
        )
    return scheduled


def total_matches(num_teams: int, double_round: bool = False) -> int:
    """Number of matches a schedule for num_teams teams will contain."""
    if num_teams < 2:
        return 0
    single = num_teams * (num_teams - 1) // 2
    return single * 2 if double_round else single


def generate_pool_schedule(
    pools: dict[str, list[str]], double_round: bool = False
) -> dict[str, list[Round]]:
    """Generate independent round-robin schedules for each named pool.

    Useful for a group stage or a league split into conferences, where
    each pool plays a full round-robin among its own teams and never
    against teams from another pool.

    Raises ValueError if the same team appears in more than one pool -
    that's almost always a data entry mistake, since a team can't be
    playing two unrelated group stages at once.
    """
    seen: dict[str, str] = {}
    for pool_name, teams in pools.items():
        for team in teams:
            if team in seen and seen[team] != pool_name:
                raise ValueError(
                    f"team {team!r} appears in multiple pools: "
                    f"{seen[team]!r} and {pool_name!r}"
                )
            seen[team] = pool_name

    return {
        pool_name: generate_round_robin(teams, double_round=double_round)
        for pool_name, teams in pools.items()
    }
