import sqlite3
from ast import literal_eval
from typing import Tuple

import coreapi
import numpy as np
import pandas as pd

from crit_app.config import DB_URI
from crit_app.job_data.job_data import caster_healer_strength, weapon_delays
from crit_app.job_data.roles import role_stat_dict
from crit_app.job_data.encounter_data import encounter_phases
from ffxiv_stats.jobs import Healer, MagicalRanged, Melee, PhysicalRanged, Tank


def etro_build(gearset_id):
    # Initialize a client & load the schema document
    client = coreapi.Client()
    schema = client.get("https://etro.gg/api/docs/")

    gearset_action = ["gearsets", "read"]
    gearset_params = {
        "id": gearset_id,
    }
    try:
        build_result = client.action(schema, gearset_action, params=gearset_params)

    except Exception as e:
        return (
            False,
            f"Etro error: {e.error.title}",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    job_abbreviated = build_result["jobAbbrev"]
    build_name = build_result["name"]

    if job_abbreviated in ("WHM", "AST", "SGE", "SCH"):
        build_role = "Healer"
        main_stat_str = "MND"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("WAR", "PLD", "DRK", "GNB"):
        build_role = "Tank"
        main_stat_str = "STR"
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BLM", "SMN", "RDM", "PCT"):
        build_role = "Magical Ranged"
        main_stat_str = "INT"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("MNK", "DRG", "SAM", "RPR", "NIN"):
        build_role = "Melee"
        main_stat_str = "STR" if job_abbreviated != "NIN" else "DEX"
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BRD", "DNC", "MCH"):
        build_role = "Physical Ranged"
        main_stat_str = "DEX"
        speed_stat_str = "SKS"

    total_params = {}

    for p in build_result["totalParams"]:
        item = dict(p)
        key = item.pop("name")
        total_params[key] = item

    primary_stat = total_params[main_stat_str]["value"]
    dh = total_params["DH"]["value"]
    ch = total_params["CRT"]["value"]
    determination = total_params["DET"]["value"]
    speed = total_params[speed_stat_str]["value"]
    wd = total_params["Weapon Damage"]["value"]
    etro_party_bonus = build_result["partyBonus"]

    if build_role == "Tank":
        secondary_stat = total_params["TEN"]["value"]

    else:
        secondary_stat = "None"

    # Weapon delay is read differently for normal weapons and relics
    # If normal weapon if the weapon key exists
    if build_result["weapon"] is not None:
        weapon_id = build_result["weapon"]
        weapon_action = ["equipment", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["delay"] / 1000

    # Relic weapon if the relic key exists
    elif build_result["relics"] is not None:
        weapon_id = build_result["relics"]["weapon"]
        weapon_action = ["relic", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["baseItem"]["delay"] / 1000

    # Fall back to hard-coded values by job if something goes wrong
    else:
        delay = weapon_delays[job_abbreviated]

    return (
        True,
        "",
        build_name,
        build_role,
        primary_stat,
        secondary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        delay,
        etro_party_bonus,
    )

def validate_main_stat(stat_name, stat_value, lower=3000, upper=6500):
    if (stat_value >= lower) and (stat_value < upper):
        return True, None
    else:
        return False, f"{stat_name} must be between 3000-6500."

def validate_meldable_stat(stat_name, stat_value, lower=380, upper=6000):
    if (stat_value >= lower) and (stat_value < upper):
        return True, None
    else:
        return False, f"{stat_name} must be between 380-5500."


def validate_secondary_stat(role, stat_value):
    if isinstance(stat_value, str):
        stat_value = float(stat_value)
    if role == "Tank":
        if (stat_value >= 380) & (stat_value < 4500):
            return True, None
        else:
            return False, "Tenacity must be between 380-4500."
    else:
        return True, None


def validate_speed_stat(speed_stat):
    """Check that speed stat is inputted and not the GCD

    Args:
        speed_stat (int, optional): Speed stat. Defaults to None.

    Returns:
        _type_: _description_
    """
    if speed_stat >= 380:
        return True, None
    else:
        return False, "Enter the speed stat, not the GCD."


def validate_weapon_damage(weapon_damage):
    if weapon_damage < 380:
        return True, None
    else:
        return False, "Weapon damage must be less than 380."


def set_secondary_stats(
    role: str, job: str, party_bonus: float, tenacity: float = None
) -> Tuple[str, int, int]:
    """Get secondary stat information based of job/role info.
    For tanks, inputted tenacity stat is just returned.

    Args:
        role (str): Role: Tank, Healer, Magical Ranged, Physical Ranged, Melee.
        job (str): 3-character abbreviated job, all caps.
        party_bonus (float): Percent bonus to main stat from each role.
        tenacity (float, optional): Tenacity value for tanks. Defaults to None.

    Raises:
        ValueError: _description_

    Returns:
        Tuple[str, int, int]: _description_
    """
    # Pre-bonus secondary stat info:
    if role in ("Melee", "Physical Ranged"):
        secondary_stat_pre_bonus = None
    elif role in ("Magical Ranged", "Healer"):
        secondary_stat_pre_bonus = caster_healer_strength[job]
    elif tenacity is None:
        raise ValueError("Internal tenacity error.")
    else:
        secondary_stat_pre_bonus = tenacity

    secondary_stat_type = (
        None
        if role in ("Melee", "Physical Ranged")
        else role_stat_dict[role]["secondary_stat"]["placeholder"].lower()
    )

    # Apply bonus if necessary
    if role in ("Healer", "Magical Ranged"):
        secondary_stat = int(secondary_stat_pre_bonus * party_bonus)
    else:
        secondary_stat = secondary_stat_pre_bonus

    return secondary_stat_type, secondary_stat_pre_bonus, secondary_stat


def read_report_table():
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    report_df = pd.read_sql_query("select * from report", con)

    cur.close()
    con.close()
    report_df["secondary_stat"] = (
        report_df["secondary_stat"]
        .replace("None", np.nan)
        .infer_objects(copy=False)
        .astype(float)
        .astype("Int64")
    )
    report_df["secondary_stat_pre_bonus"] = (
        report_df["secondary_stat_pre_bonus"]
        .replace("None", np.nan)
        .infer_objects(copy=False)
        .astype(float)
        .astype("Int64")
    )

    return report_df


def read_party_report_table():
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    report_df = pd.read_sql_query("select * from party_report", con)

    cur.close()
    con.close()
    return report_df


def read_encounter_table():
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    player_df = pd.read_sql_query("select * from encounter", con).drop_duplicates()

    cur.close()
    con.close()
    player_df["pet_ids"] = player_df["pet_ids"].apply(
        lambda x: literal_eval(x) if x is not None else x
    )
    return player_df


def update_report_table(db_row):
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


def update_party_report_table(db_row):
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


def unflag_report_recompute(analysis_id: str) -> None:
    """
    Set the recompute flag to 0 for a given analysis ID.
    
    Parameters:
    analysis_id (str): The ID of the analysis to update.
    """
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(f"""
    update report set redo_dps_pdf_flag = 0 where analysis_id = "{analysis_id}"
    """)
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

    cur.execute(f"""
    update report set redo_rotation_flag = 0 where analysis_id = "{analysis_id}"
    """)
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

    cur.execute(f"""
    update report set redo_party_report_flag = 0 where analysis_id = "{analysis_id}"
    """)
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


def format_kill_time_str(kill_time):
    return f"{int(kill_time//60):02}:{int(kill_time%60):02}.{int(round((kill_time % 60 % 1) * 1000, 0))}"


def get_phase_selector_options(furthest_phase_index: int, encounter_id: int):
    """Create a dictionary of phase select options for an encounter.
    Also create boolean indicator for whether the phase selector should be visible.

    For encounters without phases, the phase always defaults to 0 and hidden.

    Args:
        furthest_phase_index (int): Index of the furthest-reached phase for a fight ID
        encounter_id (int): ID of the encounter

    Returns:
        List of dictionaries for dbc.Select `options` argument
        Boolean for whether the selector should be visible or not.
    """
    phase_select_options = [{"label": "Entire Fight", "value": 0}]
    phase_select_hidden = True
    if encounter_id in encounter_phases.keys():
        phase_select_options.extend(
            {"label": encounter_phases[encounter_id][a], "value": a}
            for a in range(1, furthest_phase_index + 1)
        )
        phase_select_hidden = False

    return phase_select_options, phase_select_hidden


def check_prior_job_analyses(
    report_id,
    fight_id,
    player_id,
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
):
    report_df = read_report_table()
    encounter_df = read_encounter_table()
    report_df = report_df.merge(
        encounter_df[["report_id", "fight_id", "player_name", "player_id"]],
        on=["report_id", "fight_id", "player_name"],
        how="inner",
    )

    # FIXME: update with party analysis phasing
    same_fight = report_df[
        (report_df["report_id"] == report_id)
        & (report_df["fight_id"] == fight_id)
        & (report_df["player_id"] == player_id)
        & (report_df["phase_id"] == 0)
    ]

    if len(same_fight) == 0:
        return None

    build_comparison = (
        (same_fight["main_stat_pre_bonus"] == main_stat_pre_bonus)
        & (
            (same_fight["secondary_stat_pre_bonus"] == secondary_stat_pre_bonus)
            | same_fight["secondary_stat_pre_bonus"].isna()
        )
        & (same_fight["determination"] == determination)
        & (same_fight["speed"] == speed)
        & (same_fight["critical_hit"] == critical_hit)
        & (same_fight["direct_hit"] == direct_hit)
        & (same_fight["weapon_damage"] == weapon_damage)
        & (same_fight["delay"] == delay)
        & (same_fight["medication_amount"] == medication_amount)
        & (same_fight["redo_dps_pdf_flag"] == 0)
        & (same_fight["redo_rotation_flag"] == 0)
    )

    matched_record = same_fight[build_comparison]

    if len(matched_record) == 0:
        return None

    return matched_record["analysis_id"].iloc[0]


def check_prior_party_analysis(
    job_analysis_id_list: list, report_id: str, fight_id: int, party_size=8
):
    """Check if a list of job-level analysis IDs map to a party analysis ID

    Args:
        job_analysis_id_list (_type_): _description_
    """

    if len(set(job_analysis_id_list)) != party_size:
        return None, 1

    party_analysis_ids = read_party_report_table()

    party_analysis_ids = party_analysis_ids[
        (party_analysis_ids["report_id"] == report_id)
        & (party_analysis_ids["fight_id"] == fight_id)
    ]

    if len(party_analysis_ids) == 0:
        return None, 1

    all_job_analyses_match = (
        (~party_analysis_ids[party_analysis_ids.isin(job_analysis_id_list)].isna())[
            [f"analysis_id_{x+1}" for x in range(len(job_analysis_id_list))]
        ]
        .all(axis=1)
        .iloc[0]
    )

    if all_job_analyses_match:
        matched_party_analysis_id = party_analysis_ids["party_analysis_id"].iloc[0]
        recompute_flag = party_analysis_ids["redo_analysis_flag"].iloc[0]

        return matched_party_analysis_id, recompute_flag
    else:
        return None, 1


def rotation_analysis(
    role: str,
    job_no_space: str,
    rotation_df,
    t: float,
    main_stat: int,
    secondary_stat: int,
    determination: int,
    speed_stat: int,
    ch: int,
    dh: int,
    wd: int,
    delay: float,
    main_stat_pre_bonus: int,
    rotation_delta: int = 100,
    rotation_step: int = 0.5,
    action_delta: int = 10,
    compute_mgf: bool = False,
    level=100,
):
    """Analyze the rotation of a job.

    Args:
        role (str): Job role, Healer, Tank, Magical Ranged, Melee, or Physical Ranged
        job_no_space (str): Pascal case job, e.g., "WhiteMage"
        rotation_df (pandas DataFrame): rotation DataFrame
        t (float): Active fight time used to compute DPS
        main_stat (int): Amount of main stat.
        secondary_stat (int): Amount of secondary stat
        determination (int): Amount of determination stat.
        speed_stat (int): Amount of Skill/Spell Speed stat.
        ch (int): Amount of critical hit stat.
        dh (int): Amount of direct hit rate stat.
        wd (int): Amount of weapon damage stat.
        delay (float): Amount of weapon delay stat.
        main_stat_pre_bonus (int): Amount of main stat before n% party bonus, for pet attack power.

    Returns:
        ffxiv_stats job object: Object with analyzed rotation and DPS distributions.
    """

    if role == "Healer":
        job_obj = Healer(
            mind=main_stat,
            strength=secondary_stat,
            det=determination,
            spell_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
            level=level,
        )

    elif role == "Tank":
        job_obj = Tank(
            strength=main_stat,
            det=determination,
            skill_speed=speed_stat,
            tenacity=secondary_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            job=job_no_space,
            pet_attack_power=main_stat_pre_bonus,
            level=level,
        )

    elif role == "Magical Ranged":
        job_obj = MagicalRanged(
            intelligence=main_stat,
            strength=secondary_stat,
            det=determination,
            spell_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
            level=level,
        )

    elif role == "Melee":
        job_obj = Melee(
            main_stat=main_stat,
            det=determination,
            skill_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            job=job_no_space,
            pet_attack_power=main_stat_pre_bonus,
            level=level,
        )

    elif role == "Physical Ranged":
        job_obj = PhysicalRanged(
            dexterity=main_stat,
            det=determination,
            skill_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
            level=level,
        )
    else:
        raise ValueError("Incorrect role specified.")

    job_obj.attach_rotation(
        rotation_df,
        t,
        rotation_delta=rotation_delta,
        rotation_pdf_step=rotation_step,
        action_delta=action_delta,
        purge_action_moments=True,
        compute_mgf=compute_mgf,
    )

    # Check if any NaN values are in the DPS distribution
    for k, v in job_obj.unique_actions_distribution.items():
        if np.isnan(v["dps_distribution"].sum()):
            raise ValueError(f"NaN values encountered in DPS distribution for {k}")

    return job_obj
