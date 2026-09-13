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
```

`teams.txt` is one team name per line. `--format csv` is meant for
piping into a spreadsheet or another tool.

## Status

Early. The scheduler itself is solid and covered by a table-driven test
suite (`tests/test_fixtures.py`) that exercises the awkward cases: zero
and one team, odd team counts, double round-robin, duplicate names, and
that home/away is balanced rather than tied to rotation position.
Date/venue assignment and export formats beyond CSV aren't built yet.

## Development

Standard library only, no dependencies to install.

```
python -m unittest discover -s tests
```
