"""Tests for typed player-analysis access and error persistence."""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

from crit_app_v2.db import access, connection, errors
from crit_app_v2.db.player_analysis import (
    PlayerAnalysisCreationRecord,
    update_player_analysis_creation_table,
)
from crit_app_v2.db.schema import create_tables


def test_typed_access_and_error_records_write_to_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Persist access events and typed analysis errors with stable IDs."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    with closing(sqlite3.connect(database_path)) as db_connection:
        create_tables(db_connection)

    access.update_access_table(
        access.PlayerAnalysisAccess(
            analysis_id="analysis-id",
            access_datetime=datetime(2026, 11, 27, 12, 0),
        )
    )
    update_player_analysis_creation_table(
        PlayerAnalysisCreationRecord(
            analysis_id="analysis-id",
            creation_ts=datetime(2026, 11, 27, 11, 59),
        )
    )
    errors.insert_error_player_analysis(
        errors.PlayerAnalysisErrorRecord(
            report_id="abcdefghijklmnop",
            fight_id=7,
            player_id=12,
            encounter_id=93,
            encounter_name="Encounter",
            phase_id=0,
            job="Warrior",
            player_name="Player",
            main_stat_pre_bonus=4000,
            main_stat=4040,
            main_stat_type="strength",
            secondary_stat_pre_bonus=500,
            secondary_stat=500,
            secondary_stat_type="tenacity",
            determination=1500,
            speed=400,
            critical_hit=2000,
            direct_hit=1000,
            weapon_damage=100,
            delay=3.36,
            medication_amount=-1,
            party_bonus=1.01,
            error_message="analysis failed",
            traceback="traceback text",
        )
    )

    with closing(sqlite3.connect(database_path)) as db_connection:
        access_row = db_connection.execute("select analysis_id, access_datetime from access").fetchone()
        creation_row = db_connection.execute("select analysis_id, creation_ts from creation_player_analysis").fetchone()
        error_row = db_connection.execute("select error_id, error_message from error_player_analysis").fetchone()

    assert access_row == ("analysis-id", "2026-11-27T12:00:00")
    assert creation_row == ("analysis-id", "2026-11-27T11:59:00")
    assert error_row == (
        "pl-abcdefghijklmnop-7.0.12",
        "analysis failed",
    )
