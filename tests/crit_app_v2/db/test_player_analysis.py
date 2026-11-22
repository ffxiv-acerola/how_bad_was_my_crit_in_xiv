"""Tests for player-analysis database helpers."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from crit_app_v2.db import connection, player_analysis


def test_retrieve_player_analysis_information_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A lookup without a matching report returns None."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)

    with closing(sqlite3.connect(database_path)) as db_connection:
        _ = db_connection.execute(
            """
            create table encounter (
                report_id text,
                fight_id integer,
                encounter_name text,
                player_name text,
                job text,
                player_id integer,
                pet_ids text,
                excluded_enemy_ids text,
                role text,
                encounter_id integer,
                kill_time real,
                last_phase_index integer
            )
            """
        )
        _ = db_connection.execute(
            """
            create table report (
                analysis_id text,
                report_id text,
                fight_id integer,
                player_name text,
                phase_id integer,
                main_stat integer,
                main_stat_pre_bonus integer,
                secondary_stat integer,
                secondary_stat_pre_bonus integer,
                determination integer,
                speed integer,
                critical_hit integer,
                direct_hit integer,
                weapon_damage integer,
                delay real,
                party_bonus real,
                medication_amount integer,
                job_build_id text,
                job_build_provider text,
                redo_rotation_flag integer,
                redo_dps_pdf_flag integer
            )
            """
        )

    assert player_analysis.retrieve_player_analysis_information("missing") is None
