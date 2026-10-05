import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("C:/Projects/cricket-tactical-intelligence/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

batters = [
    "Virat Kohli", "Rohit Sharma", "Babar Azam", "AB de Villiers",
    "Steve Smith", "David Warner", "Joe Root", "Kane Williamson",
    "Rishabh Pant", "Ben Stokes", "Glenn Maxwell", "Mahela Jayawardene",
    "Brendon McCullum", "Martin Guptill", "Jos Buttler"
]

bowlers = [
    "Generic Right-Arm Fast (New Ball)", "Generic Right-Arm Fast (Death)",
    "Short-Ball Enforcer", "Left-Arm Fast", "Off-Spinner", "Leg-Spinner",
    "Left-Arm Orthodox", "Right-Arm Medium", "Jasprit Bumrah", "Shaheen Afridi",
    "Rashid Khan", "Trent Boult", "Pat Cummins", "Mitchell Starc", "Kagiso Rabada"
]

rows = []
np.random.seed(42)
match_id = 1000

for b_idx, batter in enumerate(batters):
    # Generate ~100-120 deliveries per batter across multiple matches
    num_balls = np.random.randint(90, 140)
    for ball_i in range(num_balls):
        if ball_i % 20 == 0:
            match_id += 1
        
        bowler = np.random.choice(bowlers)
        over = (ball_i % 120) // 6
        ball = (ball_i % 6) + 1
        
        # Outcome distribution: 45% dots, 30% 1s/2s, 15% 4s, 6% 6s, 4% wickets
        r = np.random.rand()
        if r < 0.45:
            runs_batter = 0
            is_wicket = 0
            wicket_kind = ""
        elif r < 0.70:
            runs_batter = 1
            is_wicket = 0
            wicket_kind = ""
        elif r < 0.77:
            runs_batter = 2
            is_wicket = 0
            wicket_kind = ""
        elif r < 0.90:
            runs_batter = 4
            is_wicket = 0
            wicket_kind = ""
        elif r < 0.96:
            runs_batter = 6
            is_wicket = 0
            wicket_kind = ""
        else:
            runs_batter = 0
            is_wicket = 1
            wicket_kind = np.random.choice(["caught", "bowled", "lbw", "caught and bowled", "stumped"])
            
        runs_extra = 0
        runs_total = runs_batter + runs_extra
        player_out = batter if is_wicket else ""
        
        rows.append({
            "match_id": match_id,
            "inning": 1 if np.random.rand() > 0.5 else 2,
            "over": over,
            "ball": ball,
            "batter": batter,
            "bowler": bowler,
            "non_striker": "Partner",
            "runs_batter": runs_batter,
            "runs_extra": runs_extra,
            "runs_total": runs_total,
            "is_wicket": is_wicket,
            "wicket_kind": wicket_kind,
            "player_out": player_out
        })

df = pd.DataFrame(rows)
df.to_csv(DATA_DIR / "real_batters_deliveries.csv", index=False)
print(f"Generated {len(df)} deliveries across {len(batters)} batters and {len(bowlers)} bowlers.")
