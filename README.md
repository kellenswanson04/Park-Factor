# Park Factor

Python script that computes baseball park factors from Trackman CSV data using a Baseball-Reference inspired methodology.

## Purpose

The goal of `parkfactor.py` is to estimate how much a ballpark influences scoring by comparing home run rates to a team’s road performance while adjusting for the quality of the road schedule.

## Input Data Requirements

The script expects a CSV file with at least the following columns:

- `Stadium`
- `HomeTeam`
- `AwayTeam`
- `RunsScored`
- `GameID`
- `League`
- `Level`

The CSV should represent Trackman game/event-level data where each row contains the runs scored by the home team in a game or event.

## `parkfactor.py`

### What it does

`parkfactor.py` calculates an adjusted park factor for each stadium by:

1. Measuring how many runs the home team scores per home game,
2. Comparing that to how many runs the same team scores per away game,
3. Correcting that raw ratio based on the environment of the stadiums visited on the road.

### Detailed math and logic

For each stadium, the script computes:

- `HomeRPG` = total home runs scored at the stadium / total home games at that stadium
- `AwayRPG` = total runs scored by the stadium’s principal home team as the away team / total away games
- initial park factor `iPF` = `HomeRPG / AwayRPG`

This initial park factor measures the raw home-versus-away scoring tendency.

### Adjusting for road environment

A second factor, `O_Factor`, captures the average environment of the stadiums visited by that team on the road.

- For each team, the script records the stadiums where that team played as the visitor.
- It then calculates the average `iPF` for those visited stadiums.
- That average is the team’s opponent environment or schedule-strength adjustment.

This adjustment reduces the bias introduced when a team’s away schedule is unusually hitter-friendly or pitcher-friendly.

### Final formula

The final park factor is computed as:

`PF_Raw = (iPF + O_Factor) / (1 + O_Factor)`

This formula blends the stadium’s own home/away ratio with the average park factor of its road opponents, producing a more stable estimate. This is math used by Baseball Reference in their Park Factor Calculation.

Finally, the result is scaled to a 100-style index:

`ParkFactor_100 = PF_Raw * 100`

### Why this method is stronger

`parkfactor.py` is stronger than a simple ratio-based estimate because it:

- starts with a true home-vs-away performance comparison,
- adjusts for the difficulty of the team’s road schedule,
- reduces distortion from unbalanced or extreme away venues.

This makes it a better fit for serious park factor analysis.

## Output

The script writes a CSV file named `parkfactor.csv` containing stadium-level results and intermediate values such as:

- `HomeRuns`: Total runs scored by the home team at the stadium.
- `HomeGames`: Number of home games played at the stadium.
- `HomeRPG`: Home runs per game.
- `AwayRuns`: Total runs scored by the home team as the away team.
- `AwayGames`: Number of away games played by the home team.
- `AwayRPG`: Away runs per game.
- `HomePA`: Total plate appearances by the home team at the stadium.
- `Away_PA`: Total plate appearances by the home team as the away team.
- `iPF`: Initial park factor (HomeRPG / AwayRPG).
- `O_Factor`: Average park factor of stadiums visited on the road, used to adjust for schedule strength.
- `ParkFactor_100`: Final park factor for runs, scaled to 100 (neutral), adjusted for road schedule.
- `H`: Park factor for hits per plate appearance, adjusted for road schedule.
- `1b`: Park factor for singles per plate appearance, adjusted for road schedule.
- `2b`: Park factor for doubles per plate appearance, adjusted for road schedule.
- `3b`: Park factor for triples per plate appearance, adjusted for road schedule.
- `HR`: Park factor for home runs per plate appearance, adjusted for road schedule.
- `BB`: Park factor for walks per plate appearance, adjusted for road schedule.
- `SO`: Park factor for strikeouts per plate appearance, adjusted for road schedule.
- `HardHit`: Park factor for hard-hit balls per plate appearance, adjusted for road schedule.

The `O_Factor` column is especially important because it reveals how the team’s road schedule influences the final park factor. All park factors are scaled to 100 (neutral) and rounded to the nearest integer.

## How to run

Run the script in a Python environment with `pandas`, `numpy`, and `tkinter` installed. The script opens a file picker to select the Trackman CSV.

```bash
python parkfactor.py
```

## Credit

Author: Kellen Swanson
