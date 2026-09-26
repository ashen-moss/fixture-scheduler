# fixture-scheduler

Turn a list of team names into a round-robin fixture schedule.

Every team plays every other team exactly once (or twice, home and away,
in double round-robin mode). This is the scheduling problem behind most
domestic sports leagues, and it has a few edges that are easy to get wrong
by hand: an odd number of teams needs a bye that rotates fairly, and a
double round-robin needs the return leg to actually reverse home/away
rather than just repeating the first leg.

## Library usage

```python
from fixtures import generate_round_robin

teams = ["Falcons", "Hornets", "Wolves", "Otters"]
rounds = generate_round_robin(teams)

for i, matches in enumerate(rounds, start=1):
    print(f"Round {i}")
    for home, away in matches:
        print(f"  {home} vs {away}")
```

```
Round 1
  Falcons vs Otters
  Hornets vs Wolves
Round 2
  Wolves vs Falcons
  Otters vs Hornets
Round 3
  Falcons vs Hornets
  Otters vs Wolves
```

With an odd number of teams, one team sits out each round (the bye
rotates so no team sits out twice before everyone else has):

```python
generate_round_robin(["Falcons", "Hornets", "Wolves"])
```

For a home-and-away season, pass `double_round=True`; the return leg
swaps home and away for every fixture from the first leg.

Home/away isn't assigned by raw position in the pairing - each team's
recent run of home or away games is tracked, and whichever side of a
fixture is more overdue for a change gets it, so the same team doesn't
end up with three home games in a row just because of where it landed
in the rotation.

Dates and venues aren't part of `generate_round_robin` itself - that
function only works out pairings and home/away. To turn a schedule into
dated fixtures, use `schedule_fixtures`:

```python
from datetime import date, timedelta
from fixtures import generate_round_robin, schedule_fixtures

rounds = generate_round_robin(["Falcons", "Hornets", "Wolves", "Otters"])
scheduled = schedule_fixtures(rounds, start_date=date(2026, 3, 7), interval=timedelta(days=7))

for fixture in scheduled[0]:
    print(fixture.date, fixture.home, "vs", fixture.away, "@", fixture.venue)
```

Rounds are played `interval` apart starting from `start_date`, with every
match in a round sharing that date. Venue defaults to the home team's
name; pass `venues={"Falcons": "Riverside Park", ...}` to override it for
teams that don't play at a ground named after themselves.

For a group stage or a league split into conferences, where teams only
play others in their own pool, use `generate_pool_schedule` instead. It
takes a mapping of pool name to team list and runs an independent
round-robin for each one:

```python
from fixtures import generate_pool_schedule

pools = {
    "North": ["Falcons", "Hornets", "Wolves"],
    "South": ["Otters", "Badgers", "Herons"],
}
schedules = generate_pool_schedule(pools)

for pool_name, rounds in schedules.items():
    print(f"Group {pool_name}")
    for i, matches in enumerate(rounds, start=1):
        print(f"  Round {i}")
        for home, away in matches:
            print(f"    {home} vs {away}")
```

It raises `ValueError` if the same team turns up in more than one pool,
since that's almost always a typo rather than something intentional.

To get a schedule into a calendar app, `generate_ics` turns dated fixtures
into an ICS file - each match becomes an all-day event titled `home vs
away`, located at its venue:

```python
from fixtures import generate_ics, generate_round_robin, schedule_fixtures
from datetime import date

rounds = generate_round_robin(["Falcons", "Hornets", "Wolves", "Otters"])
scheduled = schedule_fixtures(rounds, start_date=date(2026, 3, 7))
fixtures = [f for round_fixtures in scheduled for f in round_fixtures]

with open("season.ics", "w", newline="") as f:
    f.write(generate_ics(fixtures))
```

It takes a flat list of `Fixture`, so a pool schedule (a dict of rounds
per pool) needs flattening across pools first - the calendar doesn't care
how the fixtures were grouped to produce it.

## CLI usage

```
$ fixtures Falcons Hornets Wolves Otters
Round 1
  Falcons vs Otters
  Hornets vs Wolves
...

$ fixtures --from-file teams.txt --double --format csv
round,home,away
1,Falcons,Otters
1,Hornets,Wolves
...

$ fixtures Falcons Hornets Wolves Otters --start-date 2026-03-07
Round 1
  2026-03-07  Falcons vs Otters  @ Falcons
  2026-03-07  Hornets vs Wolves  @ Hornets
...

$ fixtures Falcons Hornets Wolves Otters --start-date 2026-03-07 --format ics > season.ics
```

`teams.txt` is one team name per line. `--format csv` is meant for
piping into a spreadsheet or another tool; `--format ics` produces a
calendar file and requires `--start-date`, since an ICS event needs a
date. `--start-date` turns on dated output; `--interval-days` (default 7)
controls the gap between rounds, and `--venues-file` takes a
`team,venue` CSV to override the default home-team venue.

For pool play, `--groups-file` takes a `team,group` CSV and overrides
any positional teams or `--from-file`. Each group is scheduled on its
own and the output is labeled by group:

```
$ fixtures --groups-file groups.csv --format csv
group,round,home,away
North,1,Falcons,Wolves
North,2,Hornets,Falcons
South,1,Otters,Herons
...
```

## Status

Early. The scheduler itself is solid and covered by a table-driven test
suite (`tests/test_fixtures.py`) that exercises the awkward cases: zero
and one team, odd team counts, double round-robin, duplicate names, and
that home/away is balanced rather than tied to rotation position.
Date and venue assignment are in via `schedule_fixtures`, pool play via
`generate_pool_schedule`, and calendar export via `generate_ics`
(`--format ics` on the CLI).

## Development

Standard library only, no dependencies to install.

```
python -m unittest discover -s tests
```
