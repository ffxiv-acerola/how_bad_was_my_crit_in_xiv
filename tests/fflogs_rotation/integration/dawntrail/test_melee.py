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

data_path = Path("tests/fflogs_rotation/dawntrail/melee_data/")


@pytest.mark.parametrize(
    "mock_action_table_api_via_file, mock_gql_query_integration, params",
    [
        (
            data_path / "drg_7_05_st.json",
            data_path / "drg_7_05_st.json",
            {
                "phase": 0,
                "player_id": 2,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3120,
                "job": "Dragoon",
                "expected_output_file": data_path / "drg_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/Fqar3gDdAK79bMWx?fight=10",
            },
        ),
        (
            data_path / "mnk_7_05_st.json",
            data_path / "mnk_7_05_st.json",
            {
                "phase": 0,
                "player_id": 6,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3174,
                "job": "Monk",
                "expected_output_file": data_path / "mnk_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3",
            },
        ),
        (
            data_path / "mnk_7_1_mt_phase.json",
            data_path / "mnk_7_1_mt_phase.json",
            {
                "phase": 4,
                "player_id": 23,
                "pet_ids": None,
                "excluded_enemy_ids": [52],
                "critical_hit": 2922,
                "job": "Monk",
                "expected_output_file": data_path / "mnk_7_1_mt_phase_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
        (
            data_path / "nin_7_05_st.json",
            data_path / "nin_7_05_st.json",
            {
                "phase": 0,
                "player_id": 7,
                "pet_ids": [15],
                "excluded_enemy_ids": None,
                "critical_hit": 3173,
                "job": "Ninja",
                "expected_output_file": data_path / "nin_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3",
            },
        ),
        (
            data_path / "rpr_7_05_st.json",
            data_path / "rpr_7_05_st.json",
            {
                "phase": 0,
                "player_id": 6,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 1320,
                "job": "Reaper",
                "expected_output_file": data_path / "rpr_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/tGJzXfrxPjNwWB9p?fight=12",
            },
        ),
        (
            data_path / "sam_7_05_st.json",
            data_path / "sam_7_05_st.json",
            {
                "phase": 0,
                "player_id": 3,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3103,
                "job": "Samurai",
                "expected_output_file": data_path / "sam_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/Lw7PgrFVcA1GNqnh?fight=6",
            },
        ),
        (
            data_path / "vpr_7_05_st.json",
            data_path / "vpr_7_05_st.json",
            {
                "phase": 0,
                "player_id": 81,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "critical_hit": 3173,
                "job": "Viper",
                "expected_output_file": data_path / "vpr_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/BnkfGc9vt1bRjYZm?fight=46",
            },
        ),
        (
            data_path / "vpr_7_1_mt_phase.json",
            data_path / "vpr_7_1_mt_phase.json",
            {
                "phase": 4,
                "player_id": 22,
                "pet_ids": None,
                "excluded_enemy_ids": [52],
                "critical_hit": 2922,
                "job": "Viper",
                "expected_output_file": data_path / "vpr_7_1_mt_phase_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
    ],
    indirect=["mock_action_table_api_via_file", "mock_gql_query_integration"],
)
def test_melee_end_to_end(
    mock_action_table_api_via_file, mock_gql_query_integration, params
):
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
