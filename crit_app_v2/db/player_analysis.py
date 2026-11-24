"""Database queries and updates for player analyses."""

import datetime
import json
from collections.abc import Sequence
from typing import Any

from crit_app_v2.db.connection import get_connection
from crit_app_v2.game_data import JOB_SPECS, Role


def player_analysis_meta_info(analysis_id: str) -> tuple[str, str, str, float] | None:
    """Get metadata information for a player analysis.

    Args:
        analysis_id (str): Unique analysis identifier

    Returns:
        tuple[str, str, str, float] | None
            Metadata values in player name, job, encounter name, and kill time
            order. Returns None if the analysis is not found.
    """
    sql_query = """
        select distinct
        report.player_name as player_name,
        report.job as job,
        report.encounter_name as encounter_name,
        kill_time
    from
        report
        inner join encounter using (report_id, fight_id)
    where
        analysis_id = ?
    """
    params = (analysis_id,)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)

        meta_info = cur.fetchone()

    return meta_info


def update_player_analysis_creation_table(
    db_row: tuple[str, datetime.datetime],
) -> None:
    """
    Insert or replace a record in the creation_player_analysis table.

    Args:
        db_row (tuple[str, datetime.datetime]): Analysis ID and creation timestamp.
    """
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
        insert or replace into creation_player_analysis
        values (?, ?)
        """,
            db_row,
        )


def search_prior_player_analyses(
    report_id: str,
    fight_id: int,
    fight_phase: int,
    job: str,
    player_name: str,
    main_stat_pre_bonus: int,
    secondary_stat_pre_bonus: int | None,
    determination: int,
    speed: int,
    critical_hit: int,
    direct_hit: int,
    weapon_damage: int,
    delay: float,
) -> tuple[str | None, bool]:
    """Search for matching prior player analyses in database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within report
        fight_phase (int): Phase ID within fight
        job (str): Player job/class
        player_name (str): Player name
        main_stat_pre_bonus (int): Main stat value, without bonus applied
        secondary_stat_pre_bonus (int | None): Secondary stat value, without bonus applied
        determination (int): Determination stat
        speed (int): Speed/SkS/SpS stat
        critical_hit (int): Critical hit stat
        direct_hit (int): Direct hit stat
        weapon_damage (int): Weapon damage
        delay (float): Weapon delay

    Returns:
        tuple[str | None, bool]
            Matching analysis ID and whether its redo flags are set. When no
            matching analysis exists, returns ``(None, False)``.
    """
    tank_jobs = tuple(
        spec.fflogs_name for spec in JOB_SPECS.values() if spec.role is Role.TANK
    )
    tank_placeholders = ", ".join("?" for _ in tank_jobs)
    sql_query = f"""
    SELECT
        analysis_id,
        redo_rotation_flag,
        redo_dps_pdf_flag
    FROM
        report
    WHERE
        report_id = ?
        AND fight_id = ?
        AND phase_id = ?
        AND job = ?
        AND player_name = ?
        AND main_stat_pre_bonus = ?
        AND (
            secondary_stat_pre_bonus = ?
            OR job NOT IN ({tank_placeholders})
        )
        AND determination = ?
        AND speed = ?
        AND critical_hit = ?
        AND direct_hit = ?
        AND weapon_damage = ?
        AND delay = ?
    """

    params = (
        report_id,
        fight_id,
        fight_phase,
        job,
        player_name,
        main_stat_pre_bonus,
        secondary_stat_pre_bonus,
        *tank_jobs,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        delay,
    )

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        prior_analyses = cur.fetchall()

    if len(prior_analyses) == 0:
        existing_analysis_id = None
        redo_flags = False

    elif len(prior_analyses) == 1:
        existing_analysis_id = prior_analyses[0][0]
        redo_flags = (prior_analyses[0][1] == 1) or (prior_analyses[0][2] == 1)

    else:
        raise RuntimeError("Internal error, duplicate analyses detected.")

    return existing_analysis_id, redo_flags


def check_valid_player_analysis_id(analysis_id: str | None) -> bool:
    """Check if a player analysis ID exists in the database.

    Args:
        analysis_id (str | None): Unique analysis identifier to check

    Returns:
        bool: True if analysis ID exists in database, False otherwise
    """
    if analysis_id is None:
        return False

    sql_query = """
    select
        count(analysis_id)
    from
        report
    where
        analysis_id = ?
    """
    params = (analysis_id,)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        valid_analysis_id = cur.fetchall()[0][0]

    valid_analysis_id = False if valid_analysis_id == 0 else True
    return valid_analysis_id


def retrieve_player_analysis_information(analysis_id: str) -> dict[str, Any] | None:
    """Retrieve player analysis information from database.

    Args:
        analysis_id (str): Unique analysis identifier

    Returns:
        dict[str, Any] | None
            Analysis information keyed by column name, or None if no record exists.
    """
    sql_query = """
    select
        report_id,
        fight_id,
        encounter.encounter_name as encounter_name,
        encounter.player_name as player_name,
        encounter.job as job,
        player_id,
        pet_ids,
        excluded_enemy_ids,
        role,
        encounter_id,
        kill_time,
        phase_id,
        last_phase_index,
        main_stat,
        main_stat_pre_bonus,
        secondary_stat,
        secondary_stat_pre_bonus,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        delay,
        party_bonus,
        medication_amount,
        job_build_id,
        job_build_provider,
        redo_rotation_flag,
        redo_dps_pdf_flag
    from
        encounter
        inner join report using (report_id, fight_id, player_name)
    where
        analysis_id = ?
    """
    params = (analysis_id,)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)

        columns = [col[0] for col in cur.description]
        row = cur.fetchone()
        result = dict(zip(columns, row)) if row else None

    if result is None:
        return None

    if result["pet_ids"] is not None:
        result["pet_ids"] = json.loads(result["pet_ids"])

    if result["excluded_enemy_ids"] is not None:
        result["excluded_enemy_ids"] = json.loads(result["excluded_enemy_ids"])

    return result


def update_report_table(db_row: Sequence[Any]) -> None:
    """Add a new record to the report table after a player analysis is completed."""
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
        insert or replace into report
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            db_row,
        )


def unflag_report_recompute(analysis_id: str) -> None:
    """
    Set the recompute flag to 0 for a given analysis ID.

    Parameters:
    analysis_id (str): The ID of the analysis to update.
    """
    with get_connection() as con:
        cur = con.cursor()

        cur.execute(
            """
        update report
        set
            redo_dps_pdf_flag = 0
        where
            analysis_id = ?
        """,
            (analysis_id,),
        )


def unflag_redo_rotation(analysis_id: str) -> None:
    """
    Set the redo rotation flag to 0 for a given analysis ID.

    Parameters:
        analysis_id (str): The ID of the analysis to update.
    """
    with get_connection() as con:
        cur = con.cursor()

        cur.execute(
            """
        update report
        set
            redo_rotation_flag = 0
        where
            analysis_id = ?
        """,
            (analysis_id,),
        )
