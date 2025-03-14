import sqlite3

# from ast import literal_eval
from unittest.mock import patch

import pytest

from crit_app.db_setup import (
    create_encounter_table,
    create_party_report_table,
    create_report_table,
)
from crit_app.util.db import (
    compute_party_bonus,
    get_party_analysis_calculation_info,
    get_party_analysis_player_build,
    read_player_analysis_info,
    retrieve_player_analysis_information,
    search_prior_player_analyses,
)


@pytest.fixture
def mock_db():
    """Create mock database with schema and test data."""
    con = sqlite3.connect(":memory:")
    cur = con.cursor()

    # Create tables
    cur.execute(create_encounter_table)
    cur.execute(create_report_table)
    cur.execute(create_party_report_table)

    # fmt: off
    # Insert test data for encounter table
    futures_data = [
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Althea Winter', 'Coeurl', 27, '[30]', '[55]', 'Astrologian', 'Healer'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Acedia Filianore', 'Malboro', 26, '[32]', '[55]', 'DarkKnight', 'Tank'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Shima Tsushima', 'Gilgamesh', 21, None, '[55]', 'Gunbreaker', 'Tank'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Chocolate Tea', 'Jenova', 20, '[33]', '[55]', 'Machinist', 'Physical Ranged'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Qata Mewrilah', 'Jenova', 23, None, '[55]', 'Monk', 'Melee'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Hime Chan', 'Seraph', 25, None, '[55]', 'Pictomancer', 'Magical Ranged'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Acerola Paracletus', 'Cactuar', 24, None, '[55]', 'Scholar', 'Healer'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Ayazato Suzuka', 'Sargatanas', 22, None, '[55]', 'Viper', 'Melee'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Limit Break', None, 56, None, '[55]', 'LimitBreak', 'Limit Break')
    ]
    cur.executemany(
        "INSERT INTO encounter VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        futures_data,
    )

    # Insert test data for report table
    report_data = [
        ('dd099fb5-208a-4113-b88a-b3ab827cf25f', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'DarkKnight', 'Acedia Filianore', 4841, 5083, 'Strength', 868, 868, 'Tenacity', 2310, 420, 3174, 1470, 146, 2.96, 392, 1.05, 'b8cbf432-0728-4676-ac19-c5a4b0b25cd9', "etro", 0, 0),
        ('b5902ddb-9b19-49ca-969d-5340a9b8fc23', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Gunbreaker', 'Shima Tsushima', 4820, 5061, 'Strength', 868, 868, 'Tenacity', 2310, 420, 3174, 1470, 146, 2.8, 392, 1.05, '7d3e76b0-c2e2-42e1-8c85-5466a521633f', "etro", 0, 0),
        ('27415a96-4231-4749-8a87-26826aa67264', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Astrologian', 'Althea Winter', 4885, 5129, 'Mind', None, 229, 'Strength', 2831, 420, 3041, 1014, 146, 3.2, 392, 1.05, 'b48885ce-0f5c-4bd9-8268-1fb109e178a0', "etro", 0, 0),
        ('1c7dce7e-bc96-4519-a837-9f759aca416b', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Scholar', 'Acerola Paracletus', 4883, 5127, 'Mind', None, 414, 'Strength', 2831, 420, 3041, 1014, 146, 3.12, 392, 1.05, 'e42a70d1-133a-4bc8-8867-4e7f500891b1', "etro", 0, 0),
        ('15fed881-743f-4c18-a1c0-cab626a3fdde', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Monk', 'Qata Mewrilah', 4860, 5103, 'Strength', None, None, None, 1855, 956, 3156, 1855, 146, 2.56, 392, 1.05, '4425db78-fa53-43c3-9d87-3ec6269e66ef', "etro", 0, 0),
        ('a10b2f59-8baf-47e1-a290-fd8e26ae6bc0', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Viper', 'Ayazato Suzuka', 4861, 5104, 'Strength', None, None, None, 2387, 528, 3173, 1734, 146, 2.64, 392, 1.05, '00d743c9-6426-4ad9-9956-b94a1495f1e9', "etro", 0, 0),
        ('05b19324-e677-4b16-a70f-ed4b945f683e', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Machinist', 'Chocolate Tea', 4883, 5127, 'Dexterity', None, None, None, 2091, 420, 3177, 2134, 146, 2.64, 392, 1.05, '1f7e62c9-a6ef-4bb6-9fe7-4c08e72f6280', "etro", 0, 0),
        ('1f4be7d0-2748-4bfc-9089-bd1e49684f40', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Pictomancer', 'Hime Chan', 4883, 5127, 'Intelligence', None, 203, 'Strength', 2269, 420, 3140, 1993, 146, 2.96, 392, 1.05, '4697a2b9-ef85-4079-a654-eb85501a3137', "etro", 0, 0)
    ]

    cur.executemany(
        'INSERT INTO report VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        report_data
    )
    # fmt: on

    party_report_data = [
        (
            "ccafe2ba-2433-43d2-92d7-361887ca3620",
            "ZfnF8AqRaBbzxW3w",  # report_id
            5,  # fight_id
            0,  # phase_id
            "dd099fb5-208a-4113-b88a-b3ab827cf25f",  # analysis_id_1
            "b5902ddb-9b19-49ca-969d-5340a9b8fc23",  # analysis_id_2
            "27415a96-4231-4749-8a87-26826aa67264",  # analysis_id_3
            "1c7dce7e-bc96-4519-a837-9f759aca416b",  # analysis_id_4
            "15fed881-743f-4c18-a1c0-cab626a3fdde",  # analysis_id_5
            "a10b2f59-8baf-47e1-a290-fd8e26ae6bc0",  # analysis_id_6
            "05b19324-e677-4b16-a70f-ed4b945f683e",  # analysis_id_7
            "1f4be7d0-2748-4bfc-9089-bd1e49684f40",  # analysis_id_8
            0,  # redo_analysis_flag
        )
    ]
    cur.executemany(
        """
        INSERT INTO party_report(
            party_analysis_id,
            report_id,
            fight_id,
            phase_id,
            analysis_id_1,
            analysis_id_2,
            analysis_id_3,
            analysis_id_4,
            analysis_id_5,
            analysis_id_6,
            analysis_id_7,
            analysis_id_8,
            redo_analysis_flag
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        party_report_data,
    )
    con.commit()
    return con


@pytest.fixture
def mock_sqlite_connect(mock_db):
    """Mock sqlite3.connect to return test database."""
    with patch("sqlite3.connect") as mock_connect:
        mock_connect.return_value = mock_db
        yield mock_connect


@pytest.mark.parametrize(
    "report_id, fight_id, player_id, player_name, pet_ids, excluded_enemy_ids",
    [
        ("ZfnF8AqRaBbzxW3w", 5, 27, "Althea Winter", [30], [55]),
        ("aaaaaaaaaaaaaaaaa", 0, 0, None, None, None),
    ],
)
def test_read_player_analysis_info(
    report_id,
    fight_id,
    player_id,
    player_name,
    pet_ids,
    excluded_enemy_ids,
    mock_sqlite_connect,
):
    """Test successful player info retrieval."""
    (
        player_name,
        pet_ids,
        excluded_enemy_ids,
        job,
        role,
        encounter_id,
        encounter_name,
        last_phase_index,
    ) = read_player_analysis_info("ZfnF8AqRaBbzxW3w", 5, 27)

    assert player_name == "Althea Winter"
    assert pet_ids == [30]
    assert excluded_enemy_ids == [55]
    assert job == "Astrologian"
    # assert role == "Healer"
    # assert encounter_id == 1079
    # assert encounter_name == "Futures Rewritten"
    # assert last_phase_index == 5


def test_search_prior_player_analyses(mock_sqlite_connect):
    """Test search for prior analyses."""
    existing_analysis_id, redo_flags = search_prior_player_analyses(
        report_id="ZfnF8AqRaBbzxW3w",
        fight_id=5,
        fight_phase=0,
        job="Astrologian",
        player_name="Althea Winter",
        main_stat_pre_bonus=4885,
        secondary_stat_pre_bonus=None,
        determination=2831,
        speed=420,
        critical_hit=3041,
        direct_hit=1014,
        weapon_damage=146,
        delay=3.2,
        medication_amount=392,
    )

    assert redo_flags == 0
    assert existing_analysis_id == "27415a96-4231-4749-8a87-26826aa67264"


def test_search_prior_analyses_no_match(mock_sqlite_connect):
    """Test search with no matching analyses."""
    analysis_id, redo_flag = search_prior_player_analyses(
        report_id="nonexistent",
        fight_id=999,
        fight_phase=0,
        job="Summoner",
        player_name="Missing Player",
        main_stat_pre_bonus=1,
        secondary_stat_pre_bonus=1,
        determination=1,
        speed=1,
        critical_hit=1,
        direct_hit=1,
        weapon_damage=1,
        delay=1.0,
        medication_amount=1,
    )

    assert redo_flag == 0
    assert analysis_id is None


def test_compute_party_bonus_1_05(mock_sqlite_connect):
    """Test party bonus calculation, 1.05 with LB."""
    bonus = compute_party_bonus("ZfnF8AqRaBbzxW3w", 5)

    # One unique role in test data
    assert bonus == 1.05


def test_retrieve_player_analysis_information_all_fields(mock_sqlite_connect):
    """
    Test that retrieve_player_analysis_information returns a dictionary with all.

    expected fields and correct values for the specified analysis_id.
    """
    # This analysis_id is present in our test data
    analysis_id = "27415a96-4231-4749-8a87-26826aa67264"

    analysis_info = retrieve_player_analysis_information(analysis_id)
    assert (
        analysis_info is not None
    ), "Expected a valid dictionary of analysis information."

    # Check all expected fields
    assert analysis_info["report_id"] == "ZfnF8AqRaBbzxW3w"
    assert analysis_info["fight_id"] == 5
    assert analysis_info["encounter_name"] == "Futures Rewritten"
    assert analysis_info["player_name"] == "Althea Winter"
    assert analysis_info["job"] == "Astrologian"
    assert analysis_info["player_id"] == 27
    assert analysis_info["pet_ids"] == [30]
    assert analysis_info["excluded_enemy_ids"] == [55]
    assert analysis_info["role"] == "Healer"
    assert analysis_info["encounter_id"] == 1079
    assert analysis_info["kill_time"] == 1119.081
    assert analysis_info["phase_id"] == 0
    assert analysis_info["last_phase_index"] == 5
    assert analysis_info["main_stat"] == 5129
    assert analysis_info["main_stat_pre_bonus"] == 4885
    # Our sample data has secondary_stat=None
    assert analysis_info["secondary_stat"] == 229
    assert analysis_info["secondary_stat_pre_bonus"] is None
    assert analysis_info["determination"] == 2831
    assert analysis_info["speed"] == 420
    assert analysis_info["critical_hit"] == 3041
    assert analysis_info["direct_hit"] == 1014
    assert analysis_info["weapon_damage"] == 146
    assert analysis_info["delay"] == 3.2
    assert analysis_info["party_bonus"] == 1.05
    assert analysis_info["medication_amount"] == 392
    assert analysis_info["job_build_id"] == "b48885ce-0f5c-4bd9-8268-1fb109e178a0"
    assert analysis_info["job_build_provider"] == "etro"
    assert analysis_info["redo_rotation_flag"] == 0
    assert analysis_info["redo_dps_pdf_flag"] == 0


# get_party_analysis_encounter_pet_info
# get_party_analysis_player_build
# get_party_analysis_encounter_info
def test_get_party_analysis_player_build(mock_sqlite_connect):
    """
    Test that get_party_analysis_player_build correctly retrieves all player builds.

    associated with the given party_analysis_id.
    """
    test_party_analysis_id = "ccafe2ba-2433-43d2-92d7-361887ca3620"
    # Call the function with the test party_analysis_id
    (
        etro_job_build_info,
        player_analysis_selector_opts,
        medication_amount,
    ) = get_party_analysis_player_build(test_party_analysis_id)

    # Assert medication_amount is as per the first report_data entry
    assert medication_amount == 392

    # Assert player_analysis_selector_opts has 8 entries (analysis_id_1 to analysis_id_8)
    assert len(player_analysis_selector_opts) == 8

    # Assert etro_job_build_info has 8 entries
    assert len(etro_job_build_info) == 8

    # Define expected player_analysis_selector_opts based on 'report_data'
    expected_player_analysis_selector_opts = [
        ["DarkKnight", "Acedia Filianore", "dd099fb5-208a-4113-b88a-b3ab827cf25f"],
        ["Gunbreaker", "Shima Tsushima", "b5902ddb-9b19-49ca-969d-5340a9b8fc23"],
        ["Astrologian", "Althea Winter", "27415a96-4231-4749-8a87-26826aa67264"],
        ["Scholar", "Acerola Paracletus", "1c7dce7e-bc96-4519-a837-9f759aca416b"],
        ["Monk", "Qata Mewrilah", "15fed881-743f-4c18-a1c0-cab626a3fdde"],
        ["Viper", "Ayazato Suzuka", "a10b2f59-8baf-47e1-a290-fd8e26ae6bc0"],
        ["Pictomancer", "Hime Chan", "1f4be7d0-2748-4bfc-9089-bd1e49684f40"],
        ["Machinist", "Chocolate Tea", "05b19324-e677-4b16-a70f-ed4b945f683e"],
    ]

    # Verify that all expected selector options are present
    assert sorted(player_analysis_selector_opts) == sorted(
        expected_player_analysis_selector_opts
    ), "Player analysis selector options do not match expected values."

    # Verify etro_job_build_info entries
    expected_jobs = {
        "DarkKnight",
        "Gunbreaker",
        "Astrologian",
        "Scholar",
        "Monk",
        "Viper",
        "Pictomancer",
        "Machinist",
    }
    actual_jobs = {entry["job"] for entry in etro_job_build_info}
    assert (
        actual_jobs == expected_jobs
    ), "Job names in etro_job_build_info do not match expected jobs."


@pytest.mark.parametrize(
    "report_id, fight_id, encounter_id, lb_player_id, pet_id_map",
    [
        (
            "ZfnF8AqRaBbzxW3w",
            5,
            1079,
            56,
            {
                27: [30],
                26: [32],
                21: None,
                20: [33],
                23: None,
                25: None,
                24: None,
                22: None,
                56: None,
            },
        ),
        ("aaaaaaaaaaa", 1, None, None, None),
    ],
)
def test_get_party_analysis_calculation_info_existing_record(
    report_id, fight_id, encounter_id, lb_player_id, pet_id_map, mock_sqlite_connect
):
    """
    Test that get_party_analysis_calculation_info returns correct calculation info.

    for an existing report_id and fight_id.
    """
    # Define inputs based on mock_db data
    report_id = "ZfnF8AqRaBbzxW3w"
    fight_id = 5

    # Expected outputs
    expected_encounter_id = 1079
    expected_lb_player_id = 56
    expected_pet_id_map = {
        27: [30],
        26: [32],
        21: None,
        20: [33],
        23: None,
        25: None,
        24: None,
        22: None,
        56: None,
    }

    # Call the function
    encounter_id, lb_player_id, pet_id_map = get_party_analysis_calculation_info(
        report_id, fight_id
    )

    # Assertions
    assert (
        encounter_id == expected_encounter_id
    ), "Encounter ID does not match expected value."
    assert (
        lb_player_id == expected_lb_player_id
    ), "Limit Break player ID does not match expected value."
    assert (
        pet_id_map == expected_pet_id_map
    ), "Pet ID map does not match expected values."


def test_get_party_analysis_calculation_info_nonexistent_record(mock_sqlite_connect):
    """Test that get_party_analysis_calculation_info raises an error when given a non-existent report_id and fight_id."""
    report_id = "nonexistent_report"
    fight_id = 999
    encounter_id, lb_id, _ = get_party_analysis_calculation_info(report_id, fight_id)
    assert encounter_id is None
