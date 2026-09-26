import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fixtures import (
    generate_ics,
    generate_pool_schedule,
    generate_round_robin,
    schedule_fixtures,
    total_matches,
)


def _teams_played(rounds):
    """Flatten a schedule into the set of teams that appear anywhere."""
    seen = set()
    for matches in rounds:
        for home, away in matches:
            seen.add(home)
            seen.add(away)
    return seen


class RoundRobinTableTests(unittest.TestCase):
    # Each case is (name, teams, double_round, expected_round_count,
    # expected_matches_per_round). expected_matches_per_round is None
    # when rounds have an uneven match count (odd team count -> one bye
    # per round, so every round has the same count actually; kept for clarity).
    cases = [
        ("empty", [], False, 0, None),
        ("single_team", ["A"], False, 0, None),
        ("two_teams", ["A", "B"], False, 1, 1),
        ("three_teams_bye", ["A", "B", "C"], False, 3, 1),
        ("four_teams_even", ["A", "B", "C", "D"], False, 3, 2),
        ("five_teams_bye", ["A", "B", "C", "D", "E"], False, 5, 2),
        ("four_teams_double", ["A", "B", "C", "D"], True, 6, 2),
        ("three_teams_double", ["A", "B", "C"], True, 6, 1),
    ]

    def test_round_and_match_counts(self):
        for name, teams, double_round, expected_rounds, expected_per_round in self.cases:
            with self.subTest(case=name):
                rounds = generate_round_robin(teams, double_round=double_round)
                self.assertEqual(len(rounds), expected_rounds)
                if expected_per_round is not None:
                    for matches in rounds:
                        self.assertEqual(len(matches), expected_per_round)

    def test_total_match_count_matches_helper(self):
        for name, teams, double_round, _, _ in self.cases:
            with self.subTest(case=name):
                rounds = generate_round_robin(teams, double_round=double_round)
                actual = sum(len(matches) for matches in rounds)
                self.assertEqual(actual, total_matches(len(teams), double_round))

    def test_no_team_plays_itself_or_twice_in_a_round(self):
        for name, teams, double_round, _, _ in self.cases:
            with self.subTest(case=name):
                rounds = generate_round_robin(teams, double_round=double_round)
                for matches in rounds:
                    appearing = []
                    for home, away in matches:
                        self.assertNotEqual(home, away)
                        appearing.append(home)
                        appearing.append(away)
                    self.assertEqual(len(appearing), len(set(appearing)))

    def test_every_team_appears_in_the_schedule(self):
        for name, teams, double_round, _, _ in self.cases:
            if len(teams) < 2:
                continue
            with self.subTest(case=name):
                rounds = generate_round_robin(teams, double_round=double_round)
                self.assertEqual(_teams_played(rounds), set(teams))

    def test_every_pair_meets_exactly_once_single_round(self):
        teams = ["A", "B", "C", "D", "E"]
        rounds = generate_round_robin(teams, double_round=False)
        pairs_seen = set()
        for matches in rounds:
            for home, away in matches:
                pairs_seen.add(frozenset((home, away)))
        expected_pairs = {
            frozenset((a, b))
            for i, a in enumerate(teams)
            for b in teams[i + 1 :]
        }
        self.assertEqual(pairs_seen, expected_pairs)

    def test_double_round_robin_reverses_home_and_away(self):
        teams = ["A", "B", "C", "D"]
        rounds = generate_round_robin(teams, double_round=True)
        first_leg = rounds[: len(rounds) // 2]
        second_leg = rounds[len(rounds) // 2 :]
        first_leg_pairs = {(h, a) for matches in first_leg for h, a in matches}
        second_leg_pairs = {(h, a) for matches in second_leg for h, a in matches}
        self.assertEqual(second_leg_pairs, {(a, h) for h, a in first_leg_pairs})

    def test_duplicate_team_names_raise(self):
        with self.assertRaises(ValueError):
            generate_round_robin(["A", "B", "A"])

    def test_four_teams_home_away_is_balanced_not_positional(self):
        # Regression check for the streak-avoiding home/away assignment,
        # worked out by hand for four teams.
        teams = ["A", "B", "C", "D"]
        rounds = generate_round_robin(teams, double_round=False)
        self.assertEqual(
            rounds,
            [
                [("A", "D"), ("B", "C")],
                [("C", "A"), ("D", "B")],
                [("A", "B"), ("D", "C")],
            ],
        )

    def test_breaks_are_minimized_for_four_teams(self):
        # A "break" is a team playing the same venue in two consecutive
        # rounds. Four teams over three rounds has a known minimum of two
        # breaks; an assignment that only alternates the fixed team (the
        # previous approach here) produces more.
        teams = ["A", "B", "C", "D"]
        rounds = generate_round_robin(teams, double_round=False)
        venues = {team: [] for team in teams}
        for matches in rounds:
            for home, away in matches:
                venues[home].append("H")
                venues[away].append("A")
        breaks = sum(
            1
            for history in venues.values()
            for prev, cur in zip(history, history[1:])
            if prev == cur
        )
        self.assertEqual(breaks, 2)

    def test_odd_team_bye_rotates_instead_of_always_hitting_one_team(self):
        # With 3 teams and 3 rounds, each team must sit out exactly once.
        teams = ["A", "B", "C"]
        rounds = generate_round_robin(teams, double_round=False)
        sat_out = []
        for matches in rounds:
            playing = {t for pair in matches for t in pair}
            missing = set(teams) - playing
            self.assertEqual(len(missing), 1)
            sat_out.append(next(iter(missing)))
        self.assertEqual(set(sat_out), set(teams))


class ScheduleFixturesTests(unittest.TestCase):
    def setUp(self):
        self.teams = ["A", "B", "C", "D"]
        self.rounds = generate_round_robin(self.teams)

    def test_dates_advance_by_interval_and_are_shared_within_a_round(self):
        start = date(2026, 1, 3)
        scheduled = schedule_fixtures(self.rounds, start, timedelta(days=7))
        expected_dates = [start + timedelta(days=7) * i for i in range(len(self.rounds))]
        for round_fixtures, expected in zip(scheduled, expected_dates):
            for fixture in round_fixtures:
                self.assertEqual(fixture.date, expected)

    def test_default_venue_is_the_home_team(self):
        scheduled = schedule_fixtures(self.rounds, date(2026, 1, 3))
        for round_fixtures in scheduled:
            for fixture in round_fixtures:
                self.assertEqual(fixture.venue, fixture.home)

    def test_venues_mapping_overrides_default(self):
        venues = {"A": "Riverside Park"}
        scheduled = schedule_fixtures(self.rounds, date(2026, 1, 3), venues=venues)
        for round_fixtures in scheduled:
            for fixture in round_fixtures:
                if fixture.home == "A":
                    self.assertEqual(fixture.venue, "Riverside Park")
                else:
                    self.assertEqual(fixture.venue, fixture.home)

    def test_matches_are_unchanged_home_away_pairs(self):
        scheduled = schedule_fixtures(self.rounds, date(2026, 1, 3))
        for round_fixtures, matches in zip(scheduled, self.rounds):
            self.assertEqual(
                [(f.home, f.away) for f in round_fixtures], matches
            )


class GenerateIcsTests(unittest.TestCase):
    def setUp(self):
        self.teams = ["A", "B", "C", "D"]
        rounds = generate_round_robin(self.teams)
        self.scheduled = schedule_fixtures(rounds, date(2026, 1, 3), timedelta(days=7))
        self.fixtures = [f for matches in self.scheduled for f in matches]

    def test_calendar_has_matching_begin_and_end(self):
        ics = generate_ics(self.fixtures)
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))

    def test_one_vevent_per_fixture(self):
        ics = generate_ics(self.fixtures)
        self.assertEqual(ics.count("BEGIN:VEVENT"), len(self.fixtures))
        self.assertEqual(ics.count("END:VEVENT"), len(self.fixtures))

    def test_vevent_uses_all_day_date_values_and_next_day_end(self):
        ics = generate_ics(self.fixtures)
        first = self.fixtures[0]
        start = first.date.strftime("%Y%m%d")
        end = (first.date + timedelta(days=1)).strftime("%Y%m%d")
        self.assertIn(f"DTSTART;VALUE=DATE:{start}", ics)
        self.assertIn(f"DTEND;VALUE=DATE:{end}", ics)

    def test_summary_and_location_are_present(self):
        ics = generate_ics(self.fixtures)
        first = self.fixtures[0]
        self.assertIn(f"SUMMARY:{first.home} vs {first.away}", ics)
        self.assertIn(f"LOCATION:{first.venue}", ics)

    def test_uids_are_unique(self):
        ics = generate_ics(self.fixtures)
        uids = [line for line in ics.split("\r\n") if line.startswith("UID:")]
        self.assertEqual(len(uids), len(set(uids)))

    def test_special_characters_are_escaped(self):
        fixtures = [
            schedule_fixtures(
                generate_round_robin(["Home, Inc.", "Away; Co."]),
                date(2026, 1, 3),
            )[0][0]
        ]
        ics = generate_ics(fixtures)
        self.assertIn("Home\\, Inc.", ics)
        self.assertIn("Away\\; Co.", ics)

    def test_empty_fixture_list_still_produces_valid_wrapper(self):
        ics = generate_ics([])
        self.assertEqual(ics, "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//fixture-scheduler//EN\r\n"
                          "CALSCALE:GREGORIAN\r\nX-WR-CALNAME:Fixture Schedule\r\nEND:VCALENDAR\r\n")


class PoolScheduleTests(unittest.TestCase):
    def setUp(self):
        self.pools = {
            "North": ["A", "B", "C"],
            "South": ["D", "E", "F", "G"],
        }

    def test_each_pool_gets_its_own_full_round_robin(self):
        schedules = generate_pool_schedule(self.pools)
        for pool_name, teams in self.pools.items():
            self.assertEqual(schedules[pool_name], generate_round_robin(teams))

    def test_pools_do_not_cross_schedule(self):
        schedules = generate_pool_schedule(self.pools)
        for pool_name, rounds in schedules.items():
            allowed = set(self.pools[pool_name])
            for matches in rounds:
                for home, away in matches:
                    self.assertIn(home, allowed)
                    self.assertIn(away, allowed)

    def test_double_round_is_passed_through_per_pool(self):
        schedules = generate_pool_schedule(self.pools, double_round=True)
        for pool_name, teams in self.pools.items():
            self.assertEqual(
                len(schedules[pool_name]),
                len(generate_round_robin(teams, double_round=True)),
            )

    def test_team_in_two_pools_raises(self):
        pools = {"North": ["A", "B"], "South": ["B", "C"]}
        with self.assertRaises(ValueError):
            generate_pool_schedule(pools)

    def test_empty_pools_dict_returns_empty_schedule(self):
        self.assertEqual(generate_pool_schedule({}), {})


if __name__ == "__main__":
    unittest.main()
