"""Tests for player-analysis database helpers."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from crit_app_v2.db import connection, player_analysis
from crit_app_v2.game_data import JOB_SPECS, Job, Role


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


def test_search_prior_player_analyses_reads_named_redo_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Return the matched ID and named recalculation flags from a prior row."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    with closing(sqlite3.connect(database_path)) as db_connection:
        _ = db_connection.execute(
            """
            create table report (
                analysis_id text,
                redo_rotation_flag integer,
                report_id text,
                fight_id integer,
                phase_id integer,
                job text,
                player_name text,
                main_stat_pre_bonus integer,
                secondary_stat_pre_bonus integer,
                determination integer,
                speed integer,
                critical_hit integer,
                direct_hit integer,
                weapon_damage integer,
                delay real,
                redo_dps_pdf_flag integer
            )
            """
        )
        _ = db_connection.execute(
            """
            insert into report values (
                'analysis-id', 1, 'abcdefghijklmnop', 7, 0, 'WhiteMage',
                'Player', 5000, null, 2000, 400, 2500, 1000, 145, 3.44, 0
            )
            """
        )
        db_connection.commit()

    result = player_analysis.search_prior_player_analyses(
        "abcdefghijklmnop",
        7,
        0,
        "WhiteMage",
        "Player",
        5000,
        None,
        2000,
        400,
        2500,
        1000,
        145,
        3.44,
    )

    assert result == ("analysis-id", True)


def test_search_prior_player_analyses_checks_tank_tenacity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Require matching Tenacity for a tank while ignoring it for other roles."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    with closing(sqlite3.connect(database_path)) as db_connection:
        _ = db_connection.execute(
            """
            create table report (
                analysis_id text,
                report_id text,
                fight_id integer,
                phase_id integer,
                job text,
                player_name text,
                main_stat_pre_bonus integer,
                secondary_stat_pre_bonus integer,
                determination integer,
                speed integer,
                critical_hit integer,
                direct_hit integer,
                weapon_damage integer,
                delay real,
                redo_rotation_flag integer,
                redo_dps_pdf_flag integer
            )
            """
        )
        _ = db_connection.execute(
            """
            insert into report values (
                'tank-analysis', 'abcdefghijklmnop', 7, 0, 'Warrior',
                'Player', 5000, 900, 2000, 400, 2500, 1000, 145, 3.36, 0, 0
            )
            """
        )
        db_connection.commit()

    tank_job = next(job.value for job, spec in JOB_SPECS.items() if spec.role is Role.TANK and job is Job.WARRIOR)
    mismatch = player_analysis.search_prior_player_analyses(
        "abcdefghijklmnop", 7, 0, tank_job, "Player", 5000, 800, 2000, 400, 2500, 1000, 145, 3.36
    )
    match = player_analysis.search_prior_player_analyses(
        "abcdefghijklmnop", 7, 0, tank_job, "Player", 5000, 900, 2000, 400, 2500, 1000, 145, 3.36
    )

    assert mismatch == (None, False)
    assert match == ("tank-analysis", False)
