import sqlite3

# from ast import literal_eval
from unittest.mock import patch

import pytest

from crit_app.db_setup import create_encounter_table, create_report_table
from crit_app.util.db import (
    compute_party_bonus,
    read_player_analysis_info,
    search_prior_player_analyses,
)


@pytest.fixture
def mock_db():
    """Create mock database with schema and test data"""
    con = sqlite3.connect(":memory:")
    cur = con.cursor()

    # Create tables
    cur.execute(create_encounter_table)
    cur.execute(create_report_table)

    # fmt: off
    # Insert test data for encounter table
    futures_data = [
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Althea Winter', 'Coeurl', 27, '[30]', 'Astrologian', 'Healer'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Acedia Filianore', 'Malboro', 26, '[32]', 'DarkKnight', 'Tank'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Shima Tsushima', 'Gilgamesh', 21, None, 'Gunbreaker', 'Tank'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Chocolate Tea', 'Jenova', 20, '[33]', 'Machinist', 'Physical Ranged'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Qata Mewrilah', 'Jenova', 23, None, 'Monk', 'Melee'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Hime Chan', 'Seraph', 25, None, 'Pictomancer', 'Magical Ranged'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Acerola Paracletus', 'Cactuar', 24, None, 'Scholar', 'Healer'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Ayazato Suzuka', 'Sargatanas', 22, None, 'Viper', 'Melee'),
        ('ZfnF8AqRaBbzxW3w', 5, 1079, 5, 'Futures Rewritten', 1119.081, 'Limit Break', None, 56, None, 'LimitBreak', 'Limit Break')
    ]
    cur.executemany(
        "INSERT INTO encounter VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        futures_data,
    )

    # Insert test data for report table
    report_data = [
        ('dd099fb5-208a-4113-b88a-b3ab827cf25f', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'DarkKnight', 'Acedia Filianore', 4841, 5083, 'Strength', 868, 868, 'Tenacity', 2310, 420, 3174, 1470, 146, 2.96, 392, 1.05, 'b8cbf432-0728-4676-ac19-c5a4b0b25cd9', 0, 0),
        ('b5902ddb-9b19-49ca-969d-5340a9b8fc23', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Gunbreaker', 'Shima Tsushima', 4820, 5061, 'Strength', 868, 868, 'Tenacity', 2310, 420, 3174, 1470, 146, 2.8, 392, 1.05, '7d3e76b0-c2e2-42e1-8c85-5466a521633f', 0, 0),
        ('27415a96-4231-4749-8a87-26826aa67264', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Astrologian', 'Althea Winter', 4885, 5129, 'Mind', None, 229, 'Strength', 2831, 420, 3041, 1014, 146, 3.2, 392, 1.05, 'b48885ce-0f5c-4bd9-8268-1fb109e178a0', 0, 0),
        ('1c7dce7e-bc96-4519-a837-9f759aca416b', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Scholar', 'Acerola Paracletus', 4883, 5127, 'Mind', None, 414, 'Strength', 2831, 420, 3041, 1014, 146, 3.12, 392, 1.05, 'e42a70d1-133a-4bc8-8867-4e7f500891b1', 0, 0),
        ('15fed881-743f-4c18-a1c0-cab626a3fdde', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Monk', 'Qata Mewrilah', 4860, 5103, 'Strength', None, None, None, 1855, 956, 3156, 1855, 146, 2.56, 392, 1.05, '4425db78-fa53-43c3-9d87-3ec6269e66ef', 0, 0),
        ('a10b2f59-8baf-47e1-a290-fd8e26ae6bc0', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Viper', 'Ayazato Suzuka', 4861, 5104, 'Strength', None, None, None, 2387, 528, 3173, 1734, 146, 2.64, 392, 1.05, '00d743c9-6426-4ad9-9956-b94a1495f1e9', 0, 0),
        ('05b19324-e677-4b16-a70f-ed4b945f683e', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Machinist', 'Chocolate Tea', 4883, 5127, 'Dexterity', None, None, None, 2091, 420, 3177, 2134, 146, 2.64, 392, 1.05, '1f7e62c9-a6ef-4bb6-9fe7-4c08e72f6280', 0, 0),
        ('1f4be7d0-2748-4bfc-9089-bd1e49684f40', 'ZfnF8AqRaBbzxW3w', 5, 0, 'Futures Rewritten', 832.482, 'Pictomancer', 'Hime Chan', 4883, 5127, 'Intelligence', None, 203, 'Strength', 2269, 420, 3140, 1993, 146, 2.96, 392, 1.05, '4697a2b9-ef85-4079-a654-eb85501a3137', 0, 0)
    ]

    cur.executemany(
        'INSERT INTO report VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        report_data
    )
    # fmt: on

    con.commit()
    return con


@pytest.fixture
def mock_sqlite_connect(mock_db):
    """Mock sqlite3.connect to return test database"""
    with patch("sqlite3.connect") as mock_connect:
        mock_connect.return_value = mock_db
        yield mock_connect


def test_read_player_analysis_info(mock_sqlite_connect):
    """Test successful player info retrieval"""
    player_name, pet_ids, job, role, encounter_id = read_player_analysis_info(
        "ZfnF8AqRaBbzxW3w", 5, 27
    )

    assert player_name == "Althea Winter"
    assert pet_ids == [30]
    assert job == "Astrologian"
    assert role == "Healer"
    assert encounter_id == 1079


def test_search_prior_player_analyses(mock_sqlite_connect):
    """Test search for prior analyses"""
    n_analyses, analysis_id = search_prior_player_analyses(
        report_id="ZfnF8AqRaBbzxW3w",
        fight_id=5,
        fight_phase=0,
        job="Astrologian",
        player_name="Althea Winter",
        main_stat=5129,
        secondary_stat=229,
        determination=2831,
        speed=420,
        critical_hit=3041,
        direct_hit=1014,
        weapon_damage=146,
        delay=3.2,
        medication_amount=392,
    )

    assert n_analyses == 1
    assert analysis_id == "27415a96-4231-4749-8a87-26826aa67264"


def test_search_prior_analyses_no_match(mock_sqlite_connect):
    """Test search with no matching analyses"""
    n_analyses, analysis_id = search_prior_player_analyses(
        report_id="nonexistent",
        fight_id=999,
        fight_phase=0,
        job="Summoner",
        player_name="Missing Player",
        main_stat=1,
        secondary_stat=1,
        determination=1,
        speed=1,
        critical_hit=1,
        direct_hit=1,
        weapon_damage=1,
        delay=1.0,
        medication_amount=1,
    )

    assert n_analyses == 0
    assert analysis_id is None


def test_compute_party_bonus_1_05(mock_sqlite_connect):
    """Test party bonus calculation, 1.05 with LB"""
    bonus = compute_party_bonus("ZfnF8AqRaBbzxW3w", 5)

    # One unique role in test data
    assert bonus == 1.05
