import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

# Setup File Selection
root = tk.Tk()
root.withdraw()

print("Please select your Trackman CSV file...")
file_path = filedialog.askopenfilename(
    title="Select Trackman Baseball CSV",
    filetypes=[("CSV files", "*.csv")]
)

if not file_path:
    print("No file selected. Exiting.")
    exit()

print(f"Confirmation: Reading CSV file at {file_path}...")
df = pd.read_csv(file_path, low_memory=False)

df['RunsScored'] = pd.to_numeric(df['RunsScored'], errors='coerce')
df['ExitSpeed'] = pd.to_numeric(df['ExitSpeed'], errors='coerce')

# Data Preparation: Create indicator columns for Savant-style metrics
# Standard Trackman mappings:
df['is_H'] = df['PlayResult'].isin(['Single', 'Double', 'Triple', 'HomeRun']).astype(int)
df['is_1B'] = (df['PlayResult'] == 'Single').astype(int)
df['is_2B'] = df['PlayResult'].isin(['Double']).astype(int)
df['is_3B'] = df['PlayResult'].isin(['Triple']).astype(int)
df['is_HR'] = (df['PlayResult'] == 'HomeRun').astype(int)
df['is_BB'] = (df['KorBB'] == 'Walk').astype(int)
df['is_SO'] = (df['KorBB'] == 'Strikeout').astype(int)
df['is_HardHit'] = (df['ExitSpeed'] >= 95).astype(int)
df['is_PA'] = ((df['PitchCall'] == 'InPlay') | (df['KorBB'].isin(['Walk', 'Strikeout']))).astype(int)

metrics = ['RunsScored', 'is_H', 'is_1B', 'is_2B', 'is_3B', 'is_HR', 'is_BB', 'is_SO', 'is_HardHit']

# Basic Data Aggregation
# We need runs and game counts for every stadium to get the 'Initial' Park Factor (iPF)
home_agg = {m: 'sum' for m in metrics}
home_agg.update({
    'GameID': 'nunique',
    'is_PA': 'sum',
    'HomeTeam': lambda x: x.value_counts().index[0],
    'League': 'first',
    'Level': 'first'
})

stadium_stats = df.groupby('Stadium').agg(home_agg).reset_index()
stadium_stats = stadium_stats.rename(columns={
    'RunsScored': 'HomeRuns',
    'GameID': 'HomeGames',
    'is_PA': 'HomePA'
})
stadium_stats['HomeRPG'] = stadium_stats['HomeRuns'] / stadium_stats['HomeGames']

# Calculate Road Performance for every team
away_stats = []
for team in df['HomeTeam'].unique():
    team_away_df = df[df['AwayTeam'] == team]
    if not team_away_df.empty:
        stats = {f'Away_{m}': team_away_df[m].sum() for m in metrics}
        stats['Away_PA'] = team_away_df['is_PA'].sum()
        stats['AwayGames'] = team_away_df['GameID'].nunique()
        stats['PrincipalHomeTeam'] = team
        stats['VisitedStadiums'] = team_away_df['Stadium'].unique().tolist()
        away_stats.append(stats)

away_df = pd.DataFrame(away_stats)
data = pd.merge(stadium_stats, away_df, left_on='HomeTeam', right_on='PrincipalHomeTeam', how='left')

data['AwayRuns'] = data['Away_RunsScored']
data['AwayRPG'] = data['AwayRuns'] / data['AwayGames']

# Calculate iPF (Initial Park Factor)
data['iPF'] = data['HomeRPG'] / data['AwayRPG']

# Calculate 'O' (The average iPF of the road stadiums visited)
# This is the "B-Ref Secret Sauce" - adjusting for strength of schedule
stadium_to_ipf = dict(zip(data['Stadium'], data['iPF']))

def calculate_o_factor(visited_list):
    if not isinstance(visited_list, list) or len(visited_list) == 0:
        return 1.0
    # Average the iPF of all stadiums the team played at as the visitor
    pfs = [stadium_to_ipf.get(s, 1.0) for s in visited_list]
    return sum(pfs) / len(pfs)

data['O_Factor'] = data['VisitedStadiums'].apply(calculate_o_factor)

# Baseball-Reference Formula
# Formula: PF = (iPF + O) / (1 + O)
data['PF_Raw'] = (data['iPF'] + data['O_Factor']) / (1 + data['O_Factor'])

# Final Weighting to 100
data['ParkFactor_100'] = data['PF_Raw'] * 100
data['ParkFactor_100'] = data['ParkFactor_100'].replace([np.inf, -np.inf], pd.NA)
data['ParkFactor_100'] = data['ParkFactor_100'].round(0).astype('Int64')

# Add extra metric-based park factor calculations
final_df = data[['Stadium', 'PrincipalHomeTeam', 'Level', 'League', 'HomeRuns', 'HomeGames', 'HomeRPG', 'AwayRuns', 'AwayGames', 'AwayRPG', 'HomePA', 'Away_PA', 'iPF', 'O_Factor', 'ParkFactor_100']].copy()

for m in metrics:
    if m == 'RunsScored':
        continue
    home_rate = data[m] / data['HomePA']
    away_rate = data[f'Away_{m}'] / data['Away_PA']
    col_name = m.replace("is_", "").replace("1B", "1b").replace("2B", "2b").replace("3B", "3b")

    ipf_metric = home_rate / away_rate
    ipf_metric = ipf_metric.replace([np.inf, -np.inf], pd.NA)
    ipf_map = dict(zip(data['Stadium'], ipf_metric))
    o_factor_metric = data['VisitedStadiums'].apply(
        lambda x: sum([ipf_map.get(s, 1.0) for s in x]) / len(x) if isinstance(x, list) and x else 1.0
    )

    park_factor_metric = (((ipf_metric + o_factor_metric) / (1 + o_factor_metric)) * 100)
    park_factor_metric = pd.to_numeric(park_factor_metric, errors='coerce')
    park_factor_metric = park_factor_metric.replace([np.inf, -np.inf], pd.NA)
    final_df[col_name] = park_factor_metric.round(0).astype('Int64')

# Reorder columns as specified
desired_columns = [
    'Stadium', 'PrincipalHomeTeam', 'Level', 'League', 'iPF', 'O_Factor', 'ParkFactor_100',
    'H', '1b', '2b', '3b', 'HR', 'BB', 'SO', 'HardHit',
    'HomeRuns', 'HomeGames', 'HomeRPG', 'AwayRuns', 'AwayGames', 'AwayRPG', 'HomePA', 'Away_PA'
]
final_df = final_df[desired_columns]

# Export
output_file = "parkfactor.csv"
final_df.to_csv(output_file, index=False)

print("-" * 30)
print(f"Park Factors saved to: {os.path.abspath(output_file)}")
print(f"Processed {len(final_df)} stadiums.")