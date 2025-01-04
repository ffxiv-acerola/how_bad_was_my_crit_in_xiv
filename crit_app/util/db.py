import datetime
import sqlite3
from ast import literal_eval
from typing import Any, Dict, List, Optional, Tuple, Union

from crit_app.config import DB_URI


def insert_error_analysis(
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
    """Insert error analysis information into database.

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

    Returns:
        bool: True if insert successful, False otherwise
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
        datetime.datetime.now()
    )

    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(sql_query, params)
    con.commit()
    con.close()


def read_player_analysis_info(
    report_id: str, fight_id: int, player_id: int
) -> tuple[str, str, str, int]:
    """Retrieve player analysis information from the database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within the report
        player_id (int): Player ID within the fight

    Returns:
        tuple[str, str, str, int]: Tuple containing:
            - player_name: Name of the player
            - job: Player's job/class
            - role: Player's role (Tank, Healer, etc.)
            - player_id: Player's unique identifier
    """
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(
        """
        select
            player_name,
            pet_ids,
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
    player_name, pet_ids, job, role, encounter_id, encounter_name = cur.fetchone()
    cur.close()
    con.close()
    if pet_ids is not None:
        pet_ids = literal_eval(pet_ids)
    return player_name, pet_ids, job, role, encounter_id, encounter_name


def search_prior_player_analyses(
    report_id: str,
    fight_id: int,
    fight_phase: int,
    job: str,
    player_name: str,
    main_stat: int,
    secondary_stat: int,
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
        main_stat (int): Main stat value, with bonus applied
        secondary_stat (int): Secondary stat value, with bonus applied
        determination (int): Determination stat
        speed (int): Speed/SkS/SpS stat
        critical_hit (int): Critical hit stat
        direct_hit (int): Direct hit stat
        weapon_damage (int): Weapon damage
        delay (float): Weapon delay
        medication_amount (int): Medicine/food bonus amount

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
        AND main_stat = ?
        AND secondary_stat = ?
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
        main_stat,
        secondary_stat,
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

    elif len(prior_analyses) == 1:
        existing_analysis_id = prior_analyses[0][0]

    else:
        raise RuntimeError("Internal error, duplicate analyses detected.")

    return len(prior_analyses), existing_analysis_id


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


def update_report_table(db_row):
    """
    Add a new record to the report table after a player analysis is completed.
    """
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


# def update_party_report_table(db_row):
#     con = sqlite3.connect(DB_URI)
#     cur = con.cursor()
#     cur.execute(
#         """
#         insert
#         or replace into party_report
#         values
#             (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """,
#         db_row,
#     )
#     con.commit()
#     cur.close()
#     con.close()
#     pass


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


def update_encounter_table(db_rows):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.executemany(
        """
        insert
        or replace into encounter
        values
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    get_player_analysis_job_records("ZfnF8AqRaBbzxW3w", 5)
    # retrieve_player_analysis_information("84e76865-db0a-4e4b-980a-db87e45ec0f4")
