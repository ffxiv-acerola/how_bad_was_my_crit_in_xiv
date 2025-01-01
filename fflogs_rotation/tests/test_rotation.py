import pandas as pd
from pandas.testing import assert_frame_equal

from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable
from fflogs_rotation.tests.config import headers


def pct_action_counts_by_phase(phase: int) -> pd.DataFrame:
    pct_rotation = RotationTable(
        headers,
        report_id,
        fight_id,
        "Pictomancer",
        player_id,
        crt,
        dh,
        det,
        medication,
        level,
        phase,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        pet_ids=pet_ids,
    )

    return (
        pct_rotation.rotation_df.groupby("base_action")
        .sum("n")
        .reset_index()[["base_action", "n"]]
        .sort_values(["n", "base_action"], ascending=[False, True])
        .reset_index(drop=True)
    )


report_id = "vZRCr94LWzcXYjFq"
fight_id = 15
level = 100
phase = 0
player_id = 200
pet_ids = None
main_stat = 5127
pet_attack_power = main_stat // 1.05
det = 2271
speed = 420
crt = 3140
dh = 2047
wd = 146
delay = 2.96
medication = 392

p1_actions = (
    pd.DataFrame(
        [
            {"base_action": "Star Prism", "n": 2},
            {"base_action": "Hammer Brush", "n": 3},
            {"base_action": "Thunder in Magenta", "n": 3},
            {"base_action": "Hammer Stamp", "n": 3},
            {"base_action": "Polishing Hammer", "n": 2},
            {"base_action": "Mog of the Ages", "n": 1},
            {"base_action": "Rainbow Drip", "n": 3},
            {"base_action": "Stone in Yellow", "n": 2},
            {"base_action": "Comet in Black", "n": 2},
            {"base_action": "Pom Muse", "n": 2},
            {"base_action": "Blizzard in Cyan", "n": 2},
            {"base_action": "Winged Muse", "n": 1},
            {"base_action": "Fire in Red", "n": 4},
            {"base_action": "Aero in Green", "n": 4},
            {"base_action": "Water in Blue", "n": 3},
            {"base_action": "Clawed Muse", "n": 1},
            {"base_action": "Fanged Muse", "n": 1},
        ]
    )
    .sort_values(["n", "base_action"], ascending=[False, True])
    .reset_index(drop=True)
)


p4_actions = (
    pd.DataFrame(
        [
            {"base_action": "Holy in White", "n": 14},
            {"base_action": "Comet in Black", "n": 5},
            {"base_action": "Polishing Hammer", "n": 4},
            {"base_action": "Hammer Brush", "n": 4},
            {"base_action": "Hammer Stamp", "n": 4},
            {"base_action": "Star Prism", "n": 2},
            {"base_action": "Mog of the Ages", "n": 2},
            {"base_action": "Clawed Muse", "n": 3},
            {"base_action": "Thunder in Magenta", "n": 2},
            {"base_action": "Rainbow Drip", "n": 4},
            {"base_action": "Blizzard in Cyan", "n": 2},
            {"base_action": "Stone in Yellow", "n": 2},
            {"base_action": "Pom Muse", "n": 2},
            {"base_action": "Retribution of the Madeen", "n": 2},
            {"base_action": "Fanged Muse", "n": 2},
            {"base_action": "Aero in Green", "n": 3},
            {"base_action": "Winged Muse", "n": 2},
            {"base_action": "Fire in Red", "n": 3},
            {"base_action": "Water in Blue", "n": 2},
        ]
    )
    .sort_values(["n", "base_action"], ascending=[False, True])
    .reset_index(drop=True)
)


p5_actions = (
    pd.DataFrame(
        [
            {"base_action": "Comet in Black", "n": 8},
            {"base_action": "Polishing Hammer", "n": 6},
            {"base_action": "Hammer Brush", "n": 6},
            {"base_action": "Thunder in Magenta", "n": 7},
            {"base_action": "Hammer Stamp", "n": 6},
            {"base_action": "Stone in Yellow", "n": 7},
            {"base_action": "Blizzard in Cyan", "n": 8},
            {"base_action": "Star Prism", "n": 3},
            {"base_action": "Rainbow Drip", "n": 3},
            {"base_action": "Water in Blue", "n": 7},
            {"base_action": "Aero in Green", "n": 7},
            {"base_action": "Retribution of the Madeen", "n": 2},
            {"base_action": "Winged Muse", "n": 2},
            {"base_action": "Mog of the Ages", "n": 2},
            {"base_action": "Fire in Red", "n": 7},
            {"base_action": "Holy in White", "n": 5},
            {"base_action": "Pom Muse", "n": 2},
            {"base_action": "Fanged Muse", "n": 2},
            {"base_action": "Clawed Muse", "n": 1},
        ]
    )
    .sort_values(["n", "base_action"], ascending=[False, True])
    .reset_index(drop=True)
)


def test_p1_action_counts():
    """Test that phase timing is correctly applied by action counts.

    From https://www.fflogs.com/reports/vZRCr94LWzcXYjFq?fight=15
    """
    assert_frame_equal(pct_action_counts_by_phase(phase=1), p1_actions)


def test_p4_action_counts():
    """Test that phase timing is correctly applied by action counts.

    From https://www.fflogs.com/reports/vZRCr94LWzcXYjFq?fight=15
    """
    assert_frame_equal(pct_action_counts_by_phase(phase=4), p4_actions)


def test_p5_action_counts():
    """Test that phase timing is correctly applied by action counts.

    From https://www.fflogs.com/reports/vZRCr94LWzcXYjFq?fight=15
    """
    assert_frame_equal(pct_action_counts_by_phase(phase=5), p5_actions)
