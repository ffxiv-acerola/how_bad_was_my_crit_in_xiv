from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from crit_app.job_data.encounter_data import encounter_phases
from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable

data_path = Path("tests/fflogs_rotation/integration/dawntrail/tank_data/")


@pytest.mark.parametrize(
    "mock_action_table_api_via_file, mock_gql_query_integration, params",
    [
        (
            data_path / "war_7_05_st.json",
            data_path / "war_7_05_st.json",
            {
                "phase": 0,
                "player_id": 5,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3174,
                "job": "Warrior",
                "expected_output_file": data_path / "war_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/2PhAr7tRc8GpKDNa?fight=2",
            },
        ),
        (
            data_path / "pld_7_05_st.json",
            data_path / "pld_7_05_st.json",
            {
                "phase": 0,
                "player_id": 3,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3174,
                "job": "Paladin",
                "expected_output_file": data_path / "pld_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/LP9n81AgjTQb2pXY?fight=1",
            },
        ),
        (
            data_path / "pld_7_1_mt_phase.json",
            data_path / "pld_7_1_mt_phase.json",
            {
                "phase": 4,
                "player_id": 2,
                "pet_ids": None,
                "excluded_enemy_ids": [29],
                "critical_hit": 3174,
                "job": "Paladin",
                "expected_output_file": data_path / "pld_7_1_mt_phase_expected.json",
                "log_url": "https://www.fflogs.com/reports/rJKhQHPpCk68xV3m?fight=17",
            },
        ),
        (
            data_path / "gnb_7_05_st.json",
            data_path / "gnb_7_05_st.json",
            {
                "phase": 0,
                "player_id": 9,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3174,
                "job": "Gunbreaker",
                "expected_output_file": data_path / "gnb_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3",
            },
        ),
        (
            data_path / "gnb_7_1_phase_mt.json",
            data_path / "gnb_7_1_phase_mt.json",
            {
                "phase": 4,
                "player_id": 21,
                "pet_ids": None,
                "excluded_enemy_ids": [52],
                "critical_hit": 3174,
                "job": "Gunbreaker",
                "expected_output_file": data_path / "gnb_7_1_phase_mt_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
        (
            data_path / "drk_7_05_st.json",
            data_path / "drk_7_05_st.json",
            {
                "phase": 0,
                "player_id": 2,
                "pet_ids": [13],
                "excluded_enemy_ids": None,
                "critical_hit": 3174,
                "job": "DarkKnight",
                "expected_output_file": data_path / "drk_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3",
            },
        ),
        (
            data_path / "drk_7_1_phase_mt.json",
            data_path / "drk_7_1_phase_mt.json",
            {
                "phase": 4,
                "player_id": 26,
                "pet_ids": [32],
                "excluded_enemy_ids": [52],
                "critical_hit": 3174,
                "job": "DarkKnight",
                "expected_output_file": data_path / "drk_7_1_phase_mt_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
    ],
    indirect=["mock_action_table_api_via_file", "mock_gql_query_integration"],
)
def test_tank_end_to_end(mock_action_table_api_via_file, mock_gql_query_integration, params):
    phase = params["phase"]
    player_id = params["player_id"]
    pet_ids = params["pet_ids"]
    excluded_enemy_ids = params["excluded_enemy_ids"]
    job = params["job"]
    critical_hit = params["critical_hit"]

    rt = RotationTable(
        headers={},
        report_id="",
        fight_id="",
        job=job,
        player_id=player_id,
        crit_stat=critical_hit,
        dh_stat=1000,
        determination=1000,
        medication_amt=200,
        level=100,
        phase=phase,
        damage_buff_table=damage_buff_table,
        critical_hit_rate_buff_table=critical_hit_rate_table,
        direct_hit_rate_buff_table=direct_hit_rate_table,
        guaranteed_hits_by_action_table=guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table=guaranteed_hits_by_buff_table,
        potency_table=potency_table,
        encounter_phases=encounter_phases,
        pet_ids=pet_ids,
        excluded_enemy_ids=excluded_enemy_ids,
    )
    # Assert expected behavior based on the mock JSON response

    actual_counts = (
        rt.rotation_df.groupby("base_action")
        .sum("n")
        .reset_index()[["base_action", "n"]]
        .sort_values(["n", "base_action"], ascending=[False, True])
        .reset_index(drop=True)
    )

    expected_output = (
        pd.read_json(params["expected_output_file"])
        .sort_values(["n", "base_action"], ascending=[False, True])
        .reset_index(drop=True)
    )

    assert_frame_equal(actual_counts, expected_output)
