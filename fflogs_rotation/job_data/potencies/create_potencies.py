"""
Create a main potency CSV from all job potency CSVs. Individual potencies are split by
job and by patch, to account for potency changes over time
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

# from ..game_data import patch_times
from fflogs_rotation.job_data.game_data import patch_times

if __name__ == "__main__":
    job_csv_path = Path("fflogs_rotation/job_data/potencies")
    potency_path = Path("fflogs_rotation/job_data")

    potency_df_list = []
    for p in job_csv_path.glob("**/*.csv"):
        # Get patch X.Y from X_Y-JobName.csv
        patch = float(p.stem.split("-")[0].replace("_", "."))

        # Be explicit with schema so no funny typing happens.
        potency_df = pd.read_csv(
            p,
            dtype={
                "job": "object",
                "ability_id": "Int64",
                "ability_name": "object",
                "level": "Int64",
                "buff_id": "object",
                "base_potency": "Int64",
                "damage_type": "object",
                "combo_bonus": "Int64",
                "combo_potency": "Int64",
                "positional_bonus": "Int64",
                "positional_potency": "Int64",
                "combo_positional_bonus": "Int64",
                "combo_positional_potency": "Int64",
            },
        )
        # Assign valid start/end times
        patch_start = patch_times[patch]["start"]
        patch_end = patch_times[patch]["end"]
        potency_df["valid_start"] = patch_start
        potency_df["valid_end"] = patch_end

        potency_df_list.append(potency_df)

    # Archive prior potency csv with date-prefixed filename
    if (potency_path / "potencies.csv").exists():
        today = datetime.today().strftime("%Y-%m-%d")
        shutil.move(
            potency_path / "potencies.csv", potency_path / f"{today}-potencies.csv"
        )

    pd.concat(potency_df_list).to_csv(potency_path / "potencies.csv", index=False)
