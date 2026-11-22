"""Database queries and updates for encounter records."""

from ast import literal_eval
from collections.abc import Iterable, Sequence
from typing import Any

from crit_app_v2.db.connection import get_connection


def update_encounter_table(db_rows: Iterable[Sequence[Any]]) -> None:
    """
    Insert or replace multiple records in the encounter table.

    This function takes an iterable of tuples, each representing a row of data corresponding
    to the columns in the 'encounter' table. It inserts new records or replaces existing ones
    based on the primary key constraints.

    Args:
        db_rows (Iterable[Sequence[Any]]): Rows containing values for the
            columns in the ``encounter`` table.

    Returns:
        None
    """
    with get_connection() as con:
        cur = con.cursor()
        cur.executemany(
            """
            insert
            or replace into encounter
            values
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            db_rows,
        )


def read_player_analysis_info(
    report_id: str, fight_id: int, player_id: int
) -> tuple[
    str | None,
    list[int] | None,
    list[int] | None,
    str | None,
    str | None,
    int | None,
    str | None,
    int | None,
]:
    """
    Retrieve player analysis information from the database.

    Args:
        report_id (str): FFLogs report identifier.
        fight_id (int): Fight ID within the report.
        player_id (int): Player ID within the fight.

    Returns:
        tuple[str | None, list[int] | None, list[int] | None, str | None, str | None, int | None, str | None, int | None]
            Player and encounter details, or an all-None tuple if not found.
            - player_name (str): Name of the player.
            - pet_ids (list[int] | None): List of pet IDs associated with the player,
              or None if not applicable.
            - excluded_enemy_ids (list[int] | None): List of excluded enemy IDs,
              or None if not applicable.
            - job (str): Player's job/class.
            - role (str): Player's role (e.g., Tank, Healer).
            - encounter_id (int): Identifier for the encounter.
            - encounter_name (str): Name of the encounter.
            - last_phase_index (int | None): Last phase reached in the encounter.
    """
    with get_connection() as con:
        cur = con.cursor()

        cur.execute(
            """
            select
                player_name,
                pet_ids,
                excluded_enemy_ids,
                job,
                `role`,
                encounter_id,
                encounter_name,
                last_phase_index
            from
                encounter
            where
                (report_id = ?)
                and (fight_id = ?)
                and (player_id = ?)
        """,
            (report_id, fight_id, player_id),
        )

        # Ensure that results actually exist.
        results = cur.fetchone()
        if results is None:
            return (
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
        (
            player_name,
            pet_ids,
            excluded_enemy_ids,
            job,
            role,
            encounter_id,
            encounter_name,
            last_phase_index,
        ) = results
    if pet_ids is not None:
        pet_ids = literal_eval(pet_ids)
    if excluded_enemy_ids is not None:
        excluded_enemy_ids = literal_eval(excluded_enemy_ids)
    return (
        player_name,
        pet_ids,
        excluded_enemy_ids,
        job,
        role,
        encounter_id,
        encounter_name,
        last_phase_index,
    )


def compute_party_bonus(report_id: str, fight_id: int) -> float:
    """Calculate party composition bonus based on unique roles.

    Calculates the bonus multiplier from having different roles in the party.
    Each unique role (Tank, Healer, Melee DPS, etc.) adds 1% to the base multiplier of 1.0.
    Limit Break is excluded from this calculation.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within the report

    Returns:
        float: Party bonus multiplier (e.g., 1.05 for 5 unique roles)

    Example:
        >>> compute_party_bonus("abc123", 1)
        1.05  # Party with Tank, Healer, Melee, Physical Ranged, Magical Ranged
    """
    sql_query = """
        SELECT
            1. + count(distinct role) / 100.
        from
            encounter
        where
            report_id = ?
            and fight_id = ?
            and `role` != "Limit Break"
    """
    params = (report_id, fight_id)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)
        percent_bonus = cur.fetchall()[0][0]
    return percent_bonus


def get_player_analysis_job_records(
    report_id: str, fight_id: int
) -> list[dict[str, Any]]:
    """Retrieve player analysis information from database (excluding LB).

    Args:
        report_id (str): FFLogs report identifier.
        fight_id (int): Fight ID within the report.

    Returns:
        list[dict[str, Any]]
            Player records with column names as keys.
    """
    sql_query = """
    select
        player_name,
        player_id,
        job,
        role
    from
        encounter
    where
        report_id = ?
        and fight_id = ?
        and role != "Limit Break"
    """
    params = (report_id, fight_id)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)

        columns = [col[0] for col in cur.description]
        row = cur.fetchall()
        job_records = [dict(zip(columns, r)) for r in row]

    return job_records


def get_party_analysis_calculation_info(
    report_id: str, fight_id: int
) -> tuple[int | None, int | None, dict[int, list[int] | None] | None]:
    """Retrieve player information for a given party analysis.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within the report

    Returns:
        tuple[int | None, int | None, dict[int, list[int] | None] | None]
            Encounter ID, Limit Break player ID, and the player-to-pet-ID mapping.
            - encounter_id (int): Encounter ID
            - lb_player_id (int | None): Player ID for Limit Break, None if not present.
            - pet_id_map (dict[int, list[int] | None]): Mapping of player IDs to pet IDs.
    """
    sql_query = """
    select
        encounter_id,
        job,
        player_id,
        pet_ids
    from
        encounter
    where
        report_id = ?
        and fight_id = ?
    """

    params = (report_id, fight_id)

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, params)

        # Query
        rows = cur.fetchall()

    if rows == []:
        return None, None, None
    encounter_id = rows[0][0]
    lb_player_id = [r[2] for r in rows if r[1] == "LimitBreak"]
    if len(lb_player_id) == 0:
        lb_player_id = None
    else:
        lb_player_id = lb_player_id[0]

    pet_id_map = {r[2]: literal_eval(r[3]) if r[3] is not None else r[3] for r in rows}

    return encounter_id, lb_player_id, pet_id_map
