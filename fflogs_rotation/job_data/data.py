"""FFXIV game information pertaining to buffs and potencies, stored as importable pandas DataFrames."""

from pathlib import Path

import pandas as pd

base_path = Path("fflogs_rotation/job_data")

critical_hit_rate_table = pd.read_csv(
    base_path / "critical_hit_rate_buffs.csv", dtype={"buff_id": str}
)
direct_hit_rate_table = pd.read_csv(
    base_path / "direct_hit_rate_buffs.csv", dtype={"buff_id": str}
)
damage_buff_table = pd.read_csv(base_path / "damage_buffs.csv", dtype={"buff_id": str})

guaranteed_hits_by_action_table = pd.read_csv(
    base_path / "guaranteed_hits_by_action.csv"
)
guaranteed_hits_by_buff_table = pd.read_csv(
    base_path / "guaranteed_hits_by_buff.csv", dtype={"buff_id": str}
)

potency_table = pd.read_csv(base_path / "potencies.csv", dtype={"buff_id": str})
