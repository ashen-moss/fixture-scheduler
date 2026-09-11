"""Round-robin sports fixture scheduling.

The core algorithm is the standard "circle method": hold one team fixed,
rotate the rest around it once per round. With an odd number of teams a
placeholder bye slot is added so the rotation still works, then dropped
from the output.
"""

from __future__ import annotations

Match = tuple[str, str]
Round = list[Match]

_BYE = object()  # sentinel; never equal to a real team name, never printed


def generate_round_robin(teams: list[str], double_round: bool = False) -> list[Round]:
    """Return a full round-robin schedule as a list of rounds.

    Each round is a list of (home, away) pairs. With fewer than two teams
    there is nothing to schedule and an empty list is returned.

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

    rounds: list[Round] = []
    for round_num in range(num_rounds):
        arranged = [fixed] + rotating
        pairs: Round = []
        for i in range(n // 2):
            home, away = arranged[i], arranged[n - 1 - i]
            if home is _BYE or away is _BYE:
                continue
            # The fixed slot would otherwise always sit on the same side
            # of the pairing; alternate it each round so home games even out.
            if i == 0 and round_num % 2 == 1:
                home, away = away, home
            pairs.append((home, away))
        rounds.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]

    if double_round:
        return_leg = [[(away, home) for home, away in rnd] for rnd in rounds]
        rounds = rounds + return_leg

    return rounds


def total_matches(num_teams: int, double_round: bool = False) -> int:
    """Number of matches a schedule for num_teams teams will contain."""
    if num_teams < 2:
        return 0
    single = num_teams * (num_teams - 1) // 2
    return single * 2 if double_round else single
