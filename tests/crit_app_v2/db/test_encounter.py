"""Tests for encounter persistence mappings and server-side loading."""

import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic import AnyHttpUrl

from crit_app_v2.db import connection
from crit_app_v2.db.encounter import (
    encounter_to_db_rows,
    load_encounter,
    save_encounter,
)
from crit_app_v2.db.schema import create_tables
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)
from crit_app_v2.game_data import Job, Role


def _encounter(players: list[EncounterPersonnel]) -> Encounter:
    """Build a small validated encounter for persistence tests."""
    return Encounter(
        encounter_url=EncounterUrl(build_url=AnyHttpUrl("https://de.fflogs.com/reports/abcdefghijklmnop?fight=7")),
        fight_id_resolved=7,
        encounter_id=93,
        encounter_name="Black Cat",
        last_phase_index=0,
        kill_time=123.4,
        excluded_enemy_ids=[101, 102],
        players=players,
        limit_break=None,
    )


def _player(player_id: int, job: Job, role: Role) -> EncounterPersonnel:
    """Build one player record for an encounter fixture."""
    return EncounterPersonnel(
        player_name=f"Player {player_id}",
        player_server="Test Server",
        player_id=player_id,
        pet_ids=[player_id + 1000],
        job=job,
        role=role,
    )


def _prepare_database(path: Path) -> None:
    """Create the application schema in a temporary SQLite database."""
    with closing(sqlite3.connect(path)) as db_connection:
        create_tables(db_connection)
        db_connection.commit()


def test_encounter_mapper_creates_a_row_for_each_player() -> None:
    """Map encounter metadata and each player into schema-ordered rows."""
    encounter = _encounter(
        [
            _player(10, Job.WARRIOR, Role.TANK),
            _player(11, Job.WHITE_MAGE, Role.HEALER),
        ]
    )

    rows = encounter_to_db_rows(encounter)

    assert len(rows) == 2
    assert rows[0] == (
        "abcdefghijklmnop",
        7,
        93,
        0,
        "Black Cat",
        123.4,
        "Player 10",
        "Test Server",
        10,
        "[1010]",
        "[101, 102]",
        "Warrior",
        "Tank",
    )


def test_saved_encounter_loads_as_a_validated_model(monkeypatch, tmp_path: Path) -> None:
    """Save an encounter and reconstruct its typed model from server storage."""
    database_path = tmp_path / "encounters.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    _prepare_database(database_path)
    original = _encounter(
        [
            _player(10, Job.WARRIOR, Role.TANK),
            _player(11, Job.WHITE_MAGE, Role.HEALER),
        ]
    )

    save_encounter(original)
    loaded = load_encounter("abcdefghijklmnop", 7)

    assert loaded is not None
    assert loaded.encounter_url.report_id == "abcdefghijklmnop"
    assert loaded.encounter_url.fight_id == 7
    assert loaded.encounter_name == original.encounter_name
    assert loaded.players == original.players
    assert loaded.excluded_enemy_ids == original.excluded_enemy_ids
    assert loaded.limit_break is None


def test_saving_encounter_replaces_a_stale_roster(monkeypatch, tmp_path: Path) -> None:
    """Replace old fight rows so players removed from a roster do not remain."""
    database_path = tmp_path / "encounters.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    _prepare_database(database_path)

    save_encounter(
        _encounter(
            [
                _player(10, Job.WARRIOR, Role.TANK),
                _player(11, Job.WHITE_MAGE, Role.HEALER),
            ]
        )
    )
    save_encounter(_encounter([_player(10, Job.WARRIOR, Role.TANK)]))

    loaded = load_encounter("abcdefghijklmnop", 7)

    assert loaded is not None
    assert [player.player_id for player in loaded.players] == [10]


def test_load_encounter_returns_none_when_no_player_rows_exist(monkeypatch, tmp_path: Path) -> None:
    """Return None rather than fabricating encounter data for a missing key."""
    database_path = tmp_path / "encounters.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    _prepare_database(database_path)

    assert load_encounter("abcdefghijklmnop", 7) is None
