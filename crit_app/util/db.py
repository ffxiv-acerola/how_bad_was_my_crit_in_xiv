"""Database utility functions for FFXIV Critical Hit Analysis.

This module provides database interaction functions for storing and retrieving
FFXIV combat analysis data. It handles:
- Player analysis records
- Error logging
- Fight encounter data
- Party composition information

The module uses SQLite for data storage and requires the following tables:
- encounter: Stores fight encounter metadata
- report: Stores detailed analysis results
- error_player_analysis: Stores error information

Dependencies:
    sqlite3: Database interaction
    ast.literal_eval: For parsing stored pet_ids
    typing: Type hints
"""

import datetime
import sqlite3
from ast import literal_eval
from typing import Any, Dict, List, Optional, Tuple, Union

from crit_app.config import DB_URI


def player_analysis_meta_info(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata information for a player analysis.

    Args:
        analysis_id (str): Unique analysis identifier

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing:
            - player_name: Name of the player
            - job: Player's job/class
            - encounter_name: Name of the encounter
            - kill_time: Time of the kill
            Returns None if analysis_id not found
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)

    meta_info = cur.fetchone()

    cur.close()
    con.close()

    return meta_info


def update_encounter_table(db_rows):
    """
    Insert or replace multiple records in the encounter table.

    This function takes an iterable of tuples, each representing a row of data corresponding
    to the columns in the 'encounter' table. It inserts new records or replaces existing ones
    based on the primary key constraints.

    Args:
        db_rows (Iterable[Tuple[Any, ...]]): An iterable of tuples where each tuple contains
            values for all columns in the 'encounter' table.

    Returns:
        None
    """
    con = sqlite3.connect(DB_URI)
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
    con.commit()
    cur.close()
    con.close()
    pass


def update_access_table(db_row):
    """
    Update access table, keeping track of when and how much an analysis ID is accessed.

    Inputs:
        db_row - tuple, of row to insert. Contains (`analysis_id`, `access_datetime`).
    """
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert into access
    values (?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def update_player_analysis_creation_table(db_row):
    """
    Insert or replace a record in the creation_player_analysis table.

    Args:
        db_row: Tuple containing (analysis_id, creation_ts).
    """
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert or replace into creation_player_analysis
    values (?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def read_player_analysis_info(
    report_id: str, fight_id: int, player_id: int
) -> Tuple[str, Optional[List[int]], Optional[List[int]], str, str, int, str]:
    """
    Retrieve player analysis information from the database.

    Args:
        report_id (str): FFLogs report identifier.
        fight_id (int): Fight ID within the report.
        player_id (int): Player ID within the fight.

    Returns:
        Tuple[str, Optional[List[int]], Optional[List[int]], str, str, int, str]:
            - player_name (str): Name of the player.
            - pet_ids (Optional[List[int]]): List of pet IDs associated with the player,
              or None if not applicable.
            - excluded_enemy_ids (Optional[List[int]]): List of enemy IDs excluded from analysis,
              or None if not applicable.
            - job (str): Player's job/class.
            - role (str): Player's role (e.g., Tank, Healer).
            - encounter_id (int): Identifier for the encounter.
            - encounter_name (str): Name of the encounter.
    """
    con = sqlite3.connect(DB_URI)
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
            encounter_name
        from
            encounter
        where
            (report_id = ?)
            and (fight_id = ?)
            and (player_id = ?)
    """,
        (report_id, fight_id, player_id),
    )
    (
        player_name,
        pet_ids,
        excluded_enemy_ids,
        job,
        role,
        encounter_id,
        encounter_name,
    ) = cur.fetchone()
    cur.close()
    con.close()
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
    )


def compute_party_bonus(report_id: str, fight_id: int) -> str:
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    percent_bonus = cur.fetchall()[0][0]
    cur.close()
    con.close()
    return percent_bonus


#################################
##### Player analysis ############
#################################


def search_prior_player_analyses(
    report_id: str,
    fight_id: int,
    fight_phase: int,
    job: str,
    player_name: str,
    main_stat_pre_bonus: int,
    secondary_stat_pre_bonus: int,
    determination: int,
    speed: int,
    critical_hit: int,
    direct_hit: int,
    weapon_damage: int,
    delay: float,
    medication_amount: int,
) -> Tuple[int, Union[str, None]]:
    """Search for matching prior player analyses in database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within report
        fight_phase (int): Phase ID within fight
        job (str): Player job/class
        player_name (str): Player name
        main_stat_pre_bonus (int): Main stat value, without bonus applied
        secondary_stat_pre_bonus (int): Secondary stat value, without bonus applied
        determination (int): Determination stat
        speed (int): Speed/SkS/SpS stat
        critical_hit (int): Critical hit stat
        direct_hit (int): Direct hit stat
        weapon_damage (int): Weapon damage
        delay (float): Weapon delay
        medication_amount (int): Medicine addition to main stat

    Returns:
        pd.DataFrame: Matching analysis records with all columns from report table
    """
    sql_query = """
    SELECT
        *
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
            or job not in ("Gunbreaker", "Warrior", "DarkKnight", "Paladin")
        )
        AND determination = ?
        AND speed = ?
        AND critical_hit = ?
        AND direct_hit = ?
        AND weapon_damage = ?
        AND delay = ?
        AND medication_amount = ?
    """

    params = (
        report_id,
        fight_id,
        fight_phase,
        job,
        player_name,
        main_stat_pre_bonus,
        secondary_stat_pre_bonus,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        delay,
        medication_amount,
    )

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    prior_analyses = cur.fetchall()
    cur.close()
    con.close()

    if len(prior_analyses) == 0:
        existing_analysis_id = None
        redo_flags = False

    elif len(prior_analyses) == 1:
        existing_analysis_id = prior_analyses[0][0]
        redo_flags = (prior_analyses[0][-1] == 1) or (prior_analyses[0][-2] == 1)

    else:
        raise RuntimeError("Internal error, duplicate analyses detected.")

    return existing_analysis_id, redo_flags


def check_valid_player_analysis_id(analysis_id: str) -> bool:
    """Check if a player analysis ID exists in the database.

    Args:
        analysis_id (str): Unique analysis identifier to check

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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    valid_analysis_id = cur.fetchall()[0][0]
    cur.close()
    con.close()

    valid_analysis_id = False if valid_analysis_id == 0 else True
    return valid_analysis_id


# FIXME: check this is right
def retrieve_player_analysis_information(analysis_id: str) -> Dict[str, Any]:
    """Retrieve player analysis information from database.

    Args:
        analysis_id (str): Unique analysis identifier

    Returns:
        Dict[str, Any]: Analysis information with column names as keys
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
        etro_id,
        redo_rotation_flag,
        redo_dps_pdf_flag
    from
        encounter
        inner join report using (report_id, fight_id, player_name)
    where
        analysis_id = ?
    """
    params = (analysis_id,)

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)

    columns = [col[0] for col in cur.description]
    row = cur.fetchone()
    result = dict(zip(columns, row)) if row else None

    cur.close()
    con.close()

    if result["pet_ids"] is not None:
        result["pet_ids"] = literal_eval(result["pet_ids"])

    if result["excluded_enemy_ids"] is not None:
        result["excluded_enemy_ids"] = literal_eval(result["excluded_enemy_ids"])

    return result


def get_player_analysis_job_records(
    report_id: str, fight_id: int
) -> List[Dict[str, Any]]:
    """Retrieve player analysis information from database (excluding LB).

    Args:
        analysis_id (str): Unique analysis identifier

    Returns:
        List[Dict[str, Any]]: Analysis information with column names as keys
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)

    columns = [col[0] for col in cur.description]
    row = cur.fetchall()
    job_records = [dict(zip(columns, r)) for r in row]

    cur.close()
    con.close()

    return job_records


def update_report_table(db_row):
    """Add a new record to the report table after a player analysis is completed."""
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert or replace into report
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def unflag_report_recompute(analysis_id: str) -> None:
    """
    Set the recompute flag to 0 for a given analysis ID.

    Parameters:
    analysis_id (str): The ID of the analysis to update.
    """
    con = sqlite3.connect(DB_URI)
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
    con.commit()
    cur.close()
    con.close()
    pass


def unflag_redo_rotation(analysis_id: str) -> None:
    """
    Set the redo rotation flag to 0 for a given analysis ID.

    Parameters:
        analysis_id (str): The ID of the analysis to update.
    """
    con = sqlite3.connect(DB_URI)
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
    con.commit()
    cur.close()
    con.close()
    pass


def insert_error_player_analysis(
    report_id: str,
    fight_id: int,
    player_id: int,
    encounter_id: int,
    encounter_name: str,
    phase_id: int,
    job: str,
    player_name: str,
    main_stat_pre_bonus: int,
    main_stat: int,
    main_stat_type: str,
    secondary_stat_pre_bonus: Optional[int],
    secondary_stat: Optional[int],
    secondary_stat_type: Optional[str],
    determination: int,
    speed: int,
    critical_hit: int,
    direct_hit: int,
    weapon_damage: int,
    delay: float,
    medication_amount: int,
    party_bonus: float,
    error_message: str,
    traceback: str,
) -> None:
    """Insert error information for player analyses into database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within report
        player_id (int): Player ID within fight
        encounter_id (int): Encounter ID
        encounter_name (str): Name of the encounter
        phase_id (int): Phase ID within fight
        job (str): Player job/class
        player_name (str): Name of the player
        main_stat_pre_bonus (int): Pre-bonus main stat
        main_stat (int): Post-bonus main stat
        main_stat_type (str): Type of main stat
        secondary_stat_pre_bonus (Optional[int]): Pre-bonus secondary stat
        secondary_stat (Optional[int]): Post-bonus secondary stat
        secondary_stat_type (Optional[str]): Type of secondary stat
        determination (int): Determination stat
        speed (int): Speed stat
        critical_hit (int): Critical hit stat
        direct_hit (int): Direct hit stat
        weapon_damage (int): Weapon damage
        delay (float): Weapon delay
        medication_amount (int): Medicine/food bonus
        party_bonus (float): Party composition bonus
        error_message (str): Error message
        traceback (str): Error traceback
    """
    sql_query = """
    INSERT OR REPLACE INTO error_player_analysis VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )
    """

    params = (
        report_id,
        fight_id,
        player_id,
        encounter_id,
        encounter_name,
        phase_id,
        job,
        player_name,
        main_stat_pre_bonus,
        main_stat,
        main_stat_type,
        secondary_stat_pre_bonus,
        secondary_stat,
        secondary_stat_type,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        delay,
        medication_amount,
        party_bonus,
        error_message,
        traceback,
        datetime.datetime.now(),
    )

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    con.commit()
    con.close()


#################################
##### Party analysis ############
#################################


def check_valid_party_analysis_id(party_analysis_id: str) -> bool:
    """Check if a player analysis ID exists in the database.

    Args:
        party_analysis_id (str): Unique analysis identifier to check

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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    valid_party_analysis_id = cur.fetchone()[0]
    cur.close()
    con.close()

    valid_party_analysis_id = False if valid_party_analysis_id == 0 else True
    return valid_party_analysis_id


def check_prior_party_analysis_via_player_analyses(
    player_analysis_ids: List[str],
) -> Tuple[Optional[str], int]:
    """
    Check if a party analysis entry exists for the given list of player analysis IDs.

    This function queries the 'party_report' table to determine if all eight columns
    (analysis_id_1 through analysis_id_8) match the provided list of player analysis IDs.
    If a matching row is found, it returns a tuple containing:
      - party_analysis_id (str): The ID of the existing party analysis.
      - redo_analysis_flag (int): Indicates whether the analysis should be recalculated (1) or not (0).
    If no match is found, it returns (None, 0).

    Args:
        player_analysis_ids (List[str]): A list of player analysis IDs.

    Returns:
        Tuple[Optional[str], int]:
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    prior_party_analysis_id = cur.fetchone()

    cur.close()
    con.close()

    if prior_party_analysis_id is not None:
        return prior_party_analysis_id
    else:
        return None, 0


def get_party_analysis_encounter_info(
    party_analysis_id: str,
) -> Tuple[str, int, int, int, str, float]:
    """Retrieve encounter information for a given party analysis ID.

    Args:
        party_analysis_id (str): Unique identifier for the party analysis

    Returns:
        Tuple[str, int, int, int, str, float]: Encounter information including:
            - report_id (str): FFLogs report identifier
            - fight_id (int): Fight ID within the report
            - phase_id (int): Phase ID within the fight
            - encounter_id (int): Encounter ID
            - encounter_name (str): Name of the encounter
            - kill_time (float): Time taken to complete the encounter
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

    con = sqlite3.connect(DB_URI)
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

    cur.close()
    con.close()

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
) -> Tuple[List[Dict[str, Any]], List[List[str]], int]:
    """
    Retrieve player information for a given party analysis ID.

    This function queries the database to fetch detailed information about each player
    involved in a specific party analysis. It gathers data such as player jobs, names,
    analysis IDs, pet IDs, and other relevant statistics.

    Args:
        party_analysis_id (str): Unique identifier for the party analysis.

    Returns:
        Tuple[
            List[Dict[str, Any]],            # List of dictionaries with player analysis details
            List[List[str]],                  # List of lists containing [job, player_name, analysis_id]
            int                               # Medication amount for the first player in the list
        ]:
            - etro_job_build_information (List[Dict[str, Any]]):
                A list of dictionaries where each dictionary contains detailed analysis
                information for a player, including stats and identifiers.

            - player_analysis_selector_options (List[List[str]]):
                A list of lists, each containing the job, player name, and analysis ID
                for use in selection interfaces.

            - medication_amount (int):
                The medication amount associated with the first player in the retrieved list.
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
        r.medication_amount,
        r.etro_id
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)

    # Query
    columns = [col[0] for col in cur.description]
    rows = cur.fetchall()

    # transform into outputs used by site
    etro_job_build_information = [dict(zip(columns, r)) for r in rows]
    player_analysis_selector_options = [[r[2], r[3], r[0]] for r in rows]
    medication_amount = rows[0][-2]
    cur.close()
    con.close()

    return (
        etro_job_build_information,
        player_analysis_selector_options,
        medication_amount,
    )


def get_party_analysis_calculation_info(
    report_id: str, fight_id: int
) -> Tuple[int, Optional[int], Dict[int, Optional[Any]]]:
    """Retrieve player information for a given party analysis.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within the report

    Returns:
        Tuple[int, Optional[int], Dict[int, Optional[Any]]]: Player information including:
            - encounter_id (int): Encounter ID
            - lb_player_id (Optional[int]): Player ID for Limit Break, None if not present
            - pet_id_map (Dict[int, Optional[Any]]): Mapping of player IDs to pet IDs
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

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)

    # Query
    rows = cur.fetchall()

    cur.close()
    con.close()
    encounter_id = rows[0][0]
    lb_player_id = [r[2] for r in rows if r[1] == "LimitBreak"]
    if len(lb_player_id) == 0:
        lb_player_id = None
    else:
        lb_player_id = lb_player_id[0]

    pet_id_map = {r[2]: literal_eval(r[3]) if r[3] is not None else r[3] for r in rows}

    return encounter_id, lb_player_id, pet_id_map


def update_party_report_table(db_row):
    """
    Insert or replace a record in the party_report table.

    This function takes a tuple representing a row of data corresponding to the columns
    in the 'party_report' table. It inserts a new record or replaces an existing one
    based on the primary key constraints.

    Args:
        db_row (Tuple[Any, ...]): A tuple containing values for all columns in the 'party_report' table.

    Returns:
        None
    """
    con = sqlite3.connect(DB_URI)
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
    con.commit()
    cur.close()
    con.close()
    pass


def unflag_party_report_recompute(analysis_id: str) -> None:
    """
    Set the recompute flag to 0 for a party analysis ID.

    Used after the report has been recomputed.

    Parameters:
        analysis_id (str): The ID of the party analysis to update.
    """
    con = sqlite3.connect(DB_URI)
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
    con.commit()
    cur.close()
    con.close()
    pass


def insert_error_party_analysis(
    report_id: str,
    fight_id: int,
    fight_phase: int,
    encounter_id: int,
    job: List[str],
    player_name: List[str],
    player_id: List[int],
    main_stat_no_buff: List[int],
    secondary_stat_no_buff: List[int],
    determination: List[int],
    speed: List[int],
    crit: List[int],
    dh: List[int],
    weapon_damage: List[int],
    main_stat_multiplier: List[float],
    medication_amt: int,
    etro_url: str,
    error_message: str,
    error_traceback: str,
) -> None:
    """Insert error analysis information for party into database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within report
        fight_phase (int): Phase ID within fight
        encounter_id (int): Encounter ID
        job (List[str]): List of player jobs/classes
        player_name (List[str]): List of player names
        player_id (List[int]): List of player IDs
        main_stat_no_buff (List[int]): List of main stat values without buffs
        secondary_stat_no_buff (List[int]): List of secondary stat values without buffs
        secondary_stat_type (List[str]): List of secondary stat types
        determination (List[int]): List of determination stat values
        speed (List[int]): List of speed stat values
        crit (List[int]): List of critical hit stat values
        dh (List[int]): List of direct hit stat values
        weapon_damage (List[int]): List of weapon damage values
        main_stat_multiplier (List[float]): List of main stat multipliers
        medication_amt (int): Medicine/food bonus
        error_message (str): Error message
        error_traceback (str): Error traceback
    """
    sql_query = """
    INSERT OR REPLACE INTO error_party_analysis VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )
    """

    # format into 8 rows
    rows_to_insert = []
    error_ts = datetime.datetime.now()

    for a in range(len(player_name)):
        rows_to_insert.append(
            (
                report_id,
                fight_id,
                fight_phase,
                encounter_id,
                job[a].upper(),
                player_name[a],
                player_id[a],
                main_stat_no_buff[a],
                None
                if secondary_stat_no_buff[a] == "None"
                else secondary_stat_no_buff[a],
                determination[a],
                speed[a],
                crit[a],
                dh[a],
                weapon_damage[a],
                main_stat_multiplier,
                medication_amt,
                None if etro_url[a] == "" else etro_url[a],
                error_message,
                error_traceback,
                error_ts,
            )
        )
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.executemany(sql_query, rows_to_insert)
    con.commit()
    con.close()


if __name__ == "__main__":
    # prior_analyses = search_prior_player_analyses(
    #     report_id="vNg4jJ1KMF9mt23q",
    #     fight_id=104,
    #     fight_phase=0,
    #     job="Scholar",
    #     player_name="Acerola Paracletus",
    #     main_stat=5088,
    #     secondary_stat=414,
    #     determination=3043,
    #     speed=420,
    #     critical_hit=2922,
    #     direct_hit=1158,
    #     weapon_damage=146,
    #     delay=3.12,
    #     medication_amount=392
    # )
    # get_party_analysis_player_constituents("ccafe2ba-2433-43d2-92d7-361887ca3620")
    # get_party_analysis_encounter_info("ccafe2ba-2433-43d2-92d7-361887ca3620")

    get_party_analysis_calculation_info("ZfnF8AqRaBbzxW3w", 5)
    analysis_ids = (
        "dd099fb5-208a-4113-b88a-b3ab827cf25f",
        "b5902ddb-9b19-49ca-969d-5340a9b8fc23",
        "27415a96-4231-4749-8a87-26826aa67264",
        "1c7dce7e-bc96-4519-a837-9f759aca416b",
        "15fed881-743f-4c18-a1c0-cab626a3fdde",
        "a10b2f59-8baf-47e1-a290-fd8e26ae6bc0",
        "05b19324-e677-4b16-a70f-ed4b945f683e",
        "1f4be7d0-2748-4bfc-9089-bd1e49684f40",
    )
    check_prior_party_analysis_via_player_analyses(analysis_ids)
    # retrieve_player_analysis_information("84e76865-db0a-4e4b-980a-db87e45ec0f4")
