from typing import Any, Optional, Tuple, Union

import coreapi
import numpy as np
import pandas as pd

from crit_app.job_data.encounter_data import encounter_phases
from crit_app.job_data.job_data import caster_healer_strength, weapon_delays
from crit_app.job_data.roles import role_stat_dict
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
    elif job_abbreviated in ("MNK", "DRG", "SAM", "RPR", "NIN", "VPR"):
        build_role = "Melee"
        main_stat_str = "STR" if job_abbreviated not in ("NIN", "VPR") else "DEX"
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


def validate_main_stat(
    stat_name: str, stat_value: int, lower: int = 3000, upper: int = 6500
) -> tuple[bool, str | None]:
    """
    Validate that a main stat value falls within acceptable range.

    Args:
        stat_name: Name of stat being validated
        stat_value: Stat value to check
        lower: Minimum acceptable value (default: 3000)
        upper: Maximum acceptable value (default: 6500)

    Returns:
        Tuple containing:
            - Boolean indicating if value is valid
            - Error message if invalid, None if valid

    Example:
        >>> valid, error = validate_main_stat("Strength", 3500)
        >>> assert valid and error is None

        >>> valid, error = validate_main_stat("Mind", 7000)
        >>> assert not valid
        >>> print(error)
        'Mind must be between 3000-6500.'
    """
    if (stat_value >= lower) and (stat_value < upper):
        return True, None
    else:
        return False, f"{stat_name} must be between {lower}-{upper}."


def validate_meldable_stat(
    stat_name: str, stat_value: Any, lower: int = 380, upper: int = 6000
) -> tuple[bool, str | None]:
    """
    Validate that a meldable stat value falls within an acceptable range.

    Args:
        stat_name (str): Name of the stat being validated.
        stat_value (Any): Stat value to check.
        lower (int, optional): Minimum acceptable value. Defaults to 380.
        upper (int, optional): Maximum acceptable value. Defaults to 6000.

    Returns:
        tuple:
            - bool: True if valid, False otherwise.
            - str | None: Error message if invalid, None if valid.

    Example:
        >>> valid, error = validate_meldable_stat("Critical Hit", 2000)
        >>> assert valid and error is None
    """
    # Check if stat_value is a numeric type
    if not isinstance(stat_value, (int, float)):
        try:
            # Attempt to cast stat_value to int
            stat_value = int(stat_value)
        except (ValueError, TypeError):
            error_message = f"Invalid input: stat_value for '{stat_name}' must be a number, got {type(stat_value).__name__}."
            print(error_message)
            return False, error_message

    # Perform the comparison
    if lower <= stat_value < upper:
        return True, None
    else:
        return False, f"{stat_name} must be between {lower}-{upper}."


def validate_secondary_stat(role: str, stat_value: Any) -> Tuple[bool, str | None]:
    """
    Validate secondary stat values based on role.

    Currently only validates Tenacity for Tanks.
    Other roles always return valid.

    Args:
        role (str): Player role ("Tank", "Healer", etc).
        stat_value (Any): Stat value to validate.

    Returns:
        Tuple[bool, str | None]:
            - bool: True if valid, False otherwise.
            - str | None: Error message if invalid, None if valid.

    Example:
        >>> valid, error = validate_secondary_stat("Tank", 400)
        >>> assert valid and error is None

        >>> valid, error = validate_secondary_stat("Tank", 5000)
        >>> assert not valid
        >>> print(error)
        'Tenacity must be between 380-4500.'

        >>> valid, error = validate_secondary_stat("Healer", [500])
        >>> assert not valid
        >>> print(error)
        'Invalid input: stat_value for Tenacity must be a number, got list.'
    """
    stat_name = "Tenacity"

    # Check if stat_value is a numeric type
    if not isinstance(stat_value, (int, float)):
        try:
            # Attempt to cast stat_value to float
            stat_value = float(stat_value)
        except (ValueError, TypeError):
            error_message = (
                f"Invalid input: stat_value for '{stat_name}' must be a number, "
                f"got {type(stat_value).__name__}."
            )
            print(error_message)
            return False, error_message

    if role == "Tank":
        if 380 <= stat_value < 4500:
            return True, None
        else:
            error_message = f"{stat_name} must be between 380-4500."
            print(error_message)
            return False, error_message
    else:
        return True, None


def validate_speed_stat(speed_stat: Any) -> Tuple[bool, str | None]:
    """
    Validate that input is an actual speed stat and not a GCD value.

    Args:
        speed_stat (Any): Speed stat value to validate.

    Returns:
        Tuple[bool, str | None]:
            - bool: True if valid, False otherwise.
            - str | None: Error message if invalid, None if valid.

    Example:
        >>> valid, error = validate_speed_stat(2000)  # Valid speed stat
        >>> assert valid and error is None

        >>> valid, error = validate_speed_stat(2.5)   # Invalid - GCD value
        >>> assert not valid
        >>> print(error)
        'Enter the speed stat, not the GCD.'

        >>> valid, error = validate_speed_stat("fast")   # Invalid input type
        >>> assert not valid
        >>> print(error)
        'Invalid input: speed_stat must be a number, got str.'
    """
    MIN_SPEED = 380

    # Check if speed_stat is a numeric type
    if not isinstance(speed_stat, (int, float)):
        try:
            # Attempt to cast speed_stat to float
            speed_stat = float(speed_stat)
        except (ValueError, TypeError):
            error_message = f"Invalid input: speed_stat must be a number, got {type(speed_stat).__name__}."
            print(error_message)
            return False, error_message

    if speed_stat >= MIN_SPEED:
        return True, None
    else:
        error_message = "Enter the speed stat, not the GCD."
        print(error_message)
        return False, error_message


def validate_weapon_damage(weapon_damage: Any) -> Tuple[bool, str | None]:
    """
    Validate weapon damage values.

    Args:
        weapon_damage (Any): Weapon damage value to validate.

    Returns:
        Tuple[bool, str | None]:
            - bool: True if valid, False otherwise.
            - str | None: Error message if invalid, None if valid.

    Example:
        >>> valid, error = validate_weapon_damage(350)
        >>> assert valid and error is None

        >>> valid, error = validate_weapon_damage(400)
        >>> assert not valid
        >>> print(error)
        'Weapon damage must be less than 380.'

        >>> valid, error = validate_weapon_damage("high")
        >>> assert not valid
        >>> print(error)
        'Invalid input: weapon_damage must be a number, got str.'
    """
    # Check if weapon_damage is a numeric type
    if not isinstance(weapon_damage, (int, float)):
        try:
            # Attempt to cast weapon_damage to float
            weapon_damage = float(weapon_damage)
        except (ValueError, TypeError):
            error_message = f"Invalid input: weapon_damage must be a number, got {type(weapon_damage).__name__}."
            print(error_message)
            return False, error_message

    if weapon_damage < 380:
        return True, None
    else:
        error_message = "Weapon damage must be less than 380."
        print(error_message)
        return False, error_message


def set_secondary_stats(
    role: str, job: str, party_bonus: float, tenacity: Optional[float] = None
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Get secondary stat information based on job/role info.

    Args:
        role: Role name (Tank, Healer, Magical Ranged, Physical Ranged, Melee)
        job: 3-character abbreviated job name in caps
        party_bonus: Percent bonus to main stat from each role
        tenacity: Tenacity value for tanks

    Returns:
        Tuple containing:
            - Secondary stat type name or None
            - Pre-bonus secondary stat value or None
            - Post-bonus secondary stat value or None

    Raises:
        ValueError: If tenacity is required but not provided

    Example:
        >>> type, pre, post = set_secondary_stats("Tank", "WAR", 1.05, 1500)
        >>> print(type, pre, post)
        'tenacity' 1500 1500
    """
    # Pre-bonus secondary stat info:
    if role in ("Melee", "Physical Ranged"):
        secondary_stat_pre_bonus = None
    elif role in ("Magical Ranged", "Healer"):
        secondary_stat_pre_bonus = int(caster_healer_strength[job])
    elif tenacity is None:
        raise ValueError("Internal tenacity error.")
    else:
        secondary_stat_pre_bonus = int(tenacity)

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


def format_kill_time_str(kill_time: float) -> str:
    """
    Format kill time as MM:SS.mmm string.

    Args:
        kill_time: Time in seconds to format

    Returns:
        Formatted time string "MM:SS.mmm"

    Example:
        >>> print(format_kill_time_str(123.456))
        '02:03.456'
    """
    if kill_time < 0:
        raise ValueError("Kill time cannot be negative")

    minutes = int(kill_time // 60)
    seconds = int(kill_time % 60)
    milliseconds = int(round((kill_time % 60 % 1) * 1000, 0))

    return f"{minutes:02}:{seconds:02}.{milliseconds:03}"


def get_phase_selector_options(
    furthest_phase_index: int, encounter_id: int
) -> tuple[list[dict[str, str | int]], bool]:
    """
    Create phase selector options and visibility flag for encounter.

    Args:
        furthest_phase_index: Index of furthest reached phase
        encounter_id: Encounter identifier

    Returns:
        Tuple containing:
            - List of phase options dicts with label/value pairs
            - Boolean indicating if selector should be visible

    Example:
        >>> opts, visible = get_phase_selector_options(2, 1234)
        >>> print(opts)
        [
            {"label": "Entire Fight", "value": 0},
            {"label": "Phase 1", "value": 1},
            {"label": "Phase 2", "value": 2}
        ]
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


def check_prior_party_analysis(
    job_analysis_id_list: list, report_id: str, fight_id: int, party_size=8
):
    """Check if a list of job-level analysis IDs map to a party analysis ID.

    Args:
        job_analysis_id_list (_type_): _description_
    """

    if len(set(job_analysis_id_list)) != party_size:
        return None, 1

    def read_party_report_table():
        pass

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
    rotation_df: pd.DataFrame,
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
    rotation_step: float = 0.5,
    action_delta: int = 10,
    compute_mgf: bool = False,
    level: int = 100,
    test_error_log=False,
) -> Union[Healer, Tank, MagicalRanged, Melee, PhysicalRanged]:
    """
    Analyze job rotation and compute DPS distributions.

    Args:
        role: Job role (Healer/Tank/etc)
        job_no_space: Pascal case job name
        rotation_df: Rotation data frame
        t: Fight duration in seconds
        main_stat: Main stat value
        secondary_stat: Secondary stat value
        determination: Determination stat
        speed_stat: Skill/spell speed stat
        ch: Critical hit stat
        dh: Direct hit stat
        wd: Weapon damage
        delay: Weapon delay
        main_stat_pre_bonus: Pre-bonus main stat for pets
        rotation_delta: Rotation delta value
        rotation_step: Rotation step size
        action_delta: Action delta value
        compute_mgf: Whether to compute MGF
        level: Character level

    Returns:
        Job object containing analyzed rotation and DPS distributions

    Raises:
        ValueError: If role invalid or NaN in DPS distribution

    Example:
        >>> df = pd.DataFrame(...)  # Rotation data
        >>> job = rotation_analysis(
        ...     "Healer", "WhiteMage", df,
        ...     t=360, main_stat=3000, ...
        ... )
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
    if test_error_log:
        raise ValueError("Raise test error.")
    return job_obj
