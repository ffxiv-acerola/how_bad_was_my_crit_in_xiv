"""Database queries and updates for party analyses."""

from collections.abc import Sequence
from typing import Any

from crit_app_v2.db.connection import get_connection


def check_valid_party_analysis_id(party_analysis_id: str | None) -> bool:
    """Check if a player analysis ID exists in the database.

    Args:
        party_analysis_id (str | None): Unique analysis identifier to check

    Returns:
        bool: True if analysis ID exists in database, False otherwise
    """
    if party_analysis_id is None:
        return False

    sql_query = """
    select
        count(1)
    from
        party_report
    where
        party_analysis_id = ?
    """
    params = (party_analysis_id,)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        valid_party_analysis_id = cur.fetchone()[0]

    valid_party_analysis_id = False if valid_party_analysis_id == 0 else True
    return valid_party_analysis_id


def check_prior_party_analysis_via_player_analyses(
    player_analysis_ids: list[str],
) -> tuple[str | None, int]:
    """
    Check if a party analysis entry exists for the given list of player analysis IDs.

    This function queries the 'party_report' table to determine if all eight columns
    (analysis_id_1 through analysis_id_8) match the provided list of player analysis IDs.
    If a matching row is found, it returns a tuple containing:
      - party_analysis_id (str): The ID of the existing party analysis.
      - redo_analysis_flag (int): Indicates whether the analysis should be recalculated (1) or not (0).
    If no match is found, it returns (None, 0).

    Args:
        player_analysis_ids (list[str]): A list of player analysis IDs.

    Returns:
        tuple[str | None, int]:
            A 2-tuple where the first element is the matching party_analysis_id or None,
            and the second element is the redo_analysis_flag (defaulting to 0 if not found).
    """
    placeholders = ",".join("?" for _ in player_analysis_ids)
    sql_query = f"""
    SELECT
        party_analysis_id,
        redo_analysis_flag
    FROM
        party_report
    WHERE
        analysis_id_1 IN ({placeholders})
        AND analysis_id_2 IN ({placeholders})
        AND analysis_id_3 IN ({placeholders})
        AND analysis_id_4 IN ({placeholders})
        AND analysis_id_5 IN ({placeholders})
        AND analysis_id_6 IN ({placeholders})
        AND analysis_id_7 IN ({placeholders})
        AND analysis_id_8 IN ({placeholders})
    """

    params = player_analysis_ids * 8

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        prior_party_analysis_id = cur.fetchone()

    if prior_party_analysis_id is not None:
        return prior_party_analysis_id
    else:
        return None, 0


def get_party_analysis_encounter_info(
    party_analysis_id: str,
) -> tuple[str, int, int, int | None, int, str, float, int]:
    """Retrieve encounter information for a given party analysis ID.

    Args:
        party_analysis_id (str): Unique identifier for the party analysis

    Returns:
        tuple[str, int, int, int | None, int, str, float, int]
            Encounter information including:
            - report_id (str): FFLogs report identifier
            - fight_id (int): Fight ID within the report
            - phase_id (int): Phase ID within the fight
            - last_phase_index (int | None): Last phase reached in the encounter.
            - encounter_id (int): Encounter ID
            - encounter_name (str): Name of the encounter
            - kill_time (float): Time taken to complete the encounter
            - redo_analysis_flag (int): Party-analysis recompute flag.
    """
    sql_query = """
    select DISTINCT
        report_id,
        fight_id,
        phase_id,
        last_phase_index,
        encounter_id,
        encounter_name,
        kill_time,
        redo_analysis_flag
    from
        party_report pr
        inner join encounter e using (report_id, fight_id)
    where
        party_analysis_id = ?
    """
    params = (party_analysis_id,)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        # FIXME: check if none, redirect 404
        (
            report_id,
            fight_id,
            phase_id,
            last_phase_index,
            encounter_id,
            encounter_name,
            kill_time,
            redo_analysis_flag,
        ) = cur.fetchone()

    return (
        report_id,
        fight_id,
        phase_id,
        last_phase_index,
        encounter_id,
        encounter_name,
        kill_time,
        redo_analysis_flag,
    )


def get_party_analysis_player_build(
    party_analysis_id: str,
) -> tuple[list[dict[str, Any]], list[list[str]]]:
    """
    Retrieve player information for a given party analysis ID.

    This function queries the database to fetch detailed information about each player
    involved in a specific party analysis. It gathers data such as player jobs, names,
    analysis IDs, pet IDs, and other relevant statistics.

    Args:
        party_analysis_id (str): Unique identifier for the party analysis.

    Returns:
        tuple[list[dict[str, Any]], list[list[str]]]
            - etro_job_build_information (list[dict[str, Any]]):
                A list of dictionaries where each dictionary contains detailed analysis
                information for a player, including stats and identifiers.

            - player_analysis_selector_options (list[list[str]]):
                A list of lists, each containing the job, player name, and analysis ID
                for use in selection interfaces.
    """
    sql_query = """
    SELECT distinct
        r.analysis_id,
        e.role,
        r.job,
        r.player_name,
        e.player_id,
        r.main_stat_pre_bonus,
        r.secondary_stat_pre_bonus,
        r.determination,
        r.speed,
        r.critical_hit,
        r.direct_hit,
        r.weapon_damage,
        r.delay,
        r.job_build_id,
        r.job_build_provider
    FROM
        report r
        inner join encounter e using (report_id, fight_id, player_name, job)
    WHERE r.analysis_id IN (
        SELECT analysis_id_1 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_2 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_3 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_4 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_5 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_6 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_7 FROM party_report WHERE party_analysis_id = ?
        UNION ALL
        SELECT analysis_id_8 FROM party_report WHERE party_analysis_id = ?
    )
    order by job, player_name, player_id
    """
    params = tuple([party_analysis_id] * 8)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)

        # Query
        columns = [col[0] for col in cur.description]
        rows = cur.fetchall()

        # transform into outputs used by site
        etro_job_build_information = [dict(zip(columns, r)) for r in rows]
        player_analysis_selector_options = [[r[2], r[3], r[0]] for r in rows]

    return (
        etro_job_build_information,
        player_analysis_selector_options,
    )


def update_party_report_table(db_row: Sequence[Any]) -> None:
    """
    Insert or replace a record in the party_report table.

    This function takes a tuple representing a row of data corresponding to the columns
    in the 'party_report' table. It inserts a new record or replaces an existing one
    based on the primary key constraints.

    Args:
        db_row (Sequence[Any]): Values for the columns in the ``party_report`` table.

    Returns:
        None
    """
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
            insert
            or replace into party_report
            values
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            db_row,
        )


def unflag_party_report_recompute(analysis_id: str) -> None:
    """
    Set the recompute flag to 0 for a party analysis ID.

    Used after the report has been recomputed.

    Parameters:
        analysis_id (str): The ID of the party analysis to update.
    """
    with get_connection() as con:
        cur = con.cursor()

        cur.execute(
            """
        update report
        set
            redo_party_report_flag = 0
        where
            analysis_id = ?
        """,
            (analysis_id,),
        )
