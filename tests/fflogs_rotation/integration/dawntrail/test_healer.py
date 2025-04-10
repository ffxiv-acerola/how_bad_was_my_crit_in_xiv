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

data_path = Path("tests/fflogs_rotation/integration/dawntrail/healer_data/")


@pytest.mark.parametrize(
    "mock_action_table_api_via_file, params",
    [
        (
            data_path / "ast_7_05_st.json",
            {
                "phase": 0,
                "player_id": 8,
                "pet_ids": [12],
                "excluded_enemy_ids": None,
                "job": "Astrologian",
                "expected_output_file": data_path / "ast_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3",
            },
        ),
        (
            data_path / "ast_7_1_phase_mt.json",
            {
                "phase": 2,
                "player_id": 27,
                "pet_ids": [30],
                "excluded_enemy_ids": [52],
                "job": "Astrologian",
                "expected_output_file": data_path / "ast_7_1_phase_mt_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
        (
            data_path / "ast_7_1_phase_mt_2.json",
            {
                "phase": 4,
                "player_id": 27,
                "pet_ids": [30],
                "excluded_enemy_ids": [52],
                "job": "Astrologian",
                "expected_output_file": data_path / "ast_7_1_phase_mt_2_expected.json",
                "log_url": "https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5",
            },
        ),
        (
            data_path / "sch_7_05_st.json",
            {
                "phase": 0,
                "player_id": 5,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "job": "Scholar",
                "expected_output_file": data_path / "sch_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=38",
            },
        ),
        (
            data_path / "sge_7_05_st.json",
            {
                "phase": 0,
                "player_id": 16,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "job": "Sage",
                "expected_output_file": data_path / "sge_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/Nj9P7gHwM6C1KAtQ?fight=18",
            },
        ),
        (
            data_path / "whm_7_05_st.json",
            {
                "phase": 0,
                "player_id": 24,
                "pet_ids": None,
                "excluded_enemy_ids": None,
                "job": "WhiteMage",
                "expected_output_file": data_path / "whm_7_05_st_expected.json",
                "log_url": "https://www.fflogs.com/reports/8k7xvmRyg6AVMTW1?fight=12",
            },
        ),
        (
            data_path / "whm_7_1_mt_phase.json",
            {
                "phase": 2,
                "player_id": 5,
                "pet_ids": None,
                "excluded_enemy_ids": [35],
                "job": "WhiteMage",
                "expected_output_file": data_path / "whm_7_1_mt_phase_expected.json",
                "log_url": "https://www.fflogs.com/reports/v2ZnTdW67wfXN3gQ?fight=11&type=damage-done&source=5",
            },
        ),
        (
            data_path / "whm_7_1_mt_phase.json",
            {
                "phase": 4,
                "player_id": 5,
                "pet_ids": None,
                "excluded_enemy_ids": [35],
                "job": "WhiteMage",
                "expected_output_file": data_path / "whm_7_1_mt_phase_expected.json",
                "log_url": "https://www.fflogs.com/reports/v2ZnTdW67wfXN3gQ?fight=11&type=damage-done&source=5",
            },
        ),
    ],
    indirect=["mock_action_table_api_via_file"],
)
def test_healer_end_to_end(mock_action_table_api_via_file, params):
    phase = params["phase"]
    player_id = params["player_id"]
    pet_ids = params["pet_ids"]
    excluded_enemy_ids = params["excluded_enemy_ids"]
    job = params["job"]

    rt = RotationTable(
        headers={},
        report_id="",
        fight_id="",
        job=job,
        player_id=player_id,
        crit_stat=2000,
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
