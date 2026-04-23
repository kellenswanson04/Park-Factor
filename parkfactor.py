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

# Basic Data Aggregation
# We need runs and game counts for every stadium to get the 'Initial' Park Factor (iPF)
stadium_stats = df.groupby('Stadium').agg(
    HomeRuns=('RunsScored', 'sum'),
    HomeGames=('GameID', 'nunique'),
    PrincipalHomeTeam=('HomeTeam', lambda x: x.value_counts().index[0]),
    League=('League', 'first'),
    Level=('Level', 'first')
).reset_index()

stadium_stats['HomeRPG'] = stadium_stats['HomeRuns'] / stadium_stats['HomeGames']

# Calculate Road Performance for every team
away_stats = []
for team in df['HomeTeam'].unique():
    team_away_df = df[df['AwayTeam'] == team]
    if not team_away_df.empty:
        away_runs = team_away_df['RunsScored'].sum()
        away_games = team_away_df['GameID'].nunique()
        # Track which stadiums this team visited for the 'O' factor later
        visited_stadiums = team_away_df['Stadium'].unique().tolist()
        
        away_stats.append({
            'PrincipalHomeTeam': team,
            'AwayRuns': away_runs,
            'AwayGames': away_games,
            'AwayRPG': away_runs / away_games,
            'VisitedStadiums': visited_stadiums
        })

away_df = pd.DataFrame(away_stats)
data = pd.merge(stadium_stats, away_df, on='PrincipalHomeTeam', how='left')

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

# Clean up the dataframe for output (remove list columns)
output_cols = [
    'Stadium', 'PrincipalHomeTeam', 'Level', 'League', 
    'HomeRuns', 'HomeGames', 'HomeRPG', 
    'AwayRuns', 'AwayGames', 'AwayRPG', 
    'iPF', 'O_Factor', 'ParkFactor_100'
]
final_df = data[output_cols]

# Export
output_file = "parkfactor.csv"
final_df.to_csv(output_file, index=False)

print("-" * 30)
print(f"Park Factors saved to: {os.path.abspath(output_file)}")
print(f"Processed {len(final_df)} stadiums.")