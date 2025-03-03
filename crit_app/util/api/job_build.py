from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import coreapi
import requests

from crit_app.job_data.job_data import weapon_delays

ETRO_JOB_STATS = {
    "WHM": ("Healer", "MND", "SPS"),
    "AST": ("Healer", "MND", "SPS"),
    "SGE": ("Healer", "MND", "SPS"),
    "SCH": ("Healer", "MND", "SPS"),
    "WAR": ("Tank", "STR", "SKS"),
    "PLD": ("Tank", "STR", "SKS"),
    "DRK": ("Tank", "STR", "SKS"),
    "GNB": ("Tank", "STR", "SKS"),
    "BLM": ("Magical Ranged", "INT", "SPS"),
    "SMN": ("Magical Ranged", "INT", "SPS"),
    "RDM": ("Magical Ranged", "INT", "SPS"),
    "PCT": ("Magical Ranged", "INT", "SPS"),
    "MNK": ("Melee", "STR", "SKS"),
    "DRG": ("Melee", "STR", "SKS"),
    "SAM": ("Melee", "STR", "SKS"),
    "RPR": ("Melee", "STR", "SKS"),
    "NIN": ("Melee", "DEX", "SKS"),
    "VPR": ("Melee", "DEX", "SKS"),
    "BRD": ("Physical Ranged", "DEX", "SKS"),
    "DNC": ("Physical Ranged", "DEX", "SKS"),
    "MCH": ("Physical Ranged", "DEX", "SKS"),
}

ERROR_CODE_MAP = {
    1: "Only etro.gg or xivgear.app is supported.",
    2: "URL does not link to valid build.",
    3: "Error retrieving build.",
}


def job_build_provider(job_build_url: str) -> tuple[bool, str]:
    """Check if the required domain elements are present.

    Args:
        job_build_url (str): URL to the job build.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating if the URL is valid and the provider name or error message.
    """
    INVALID_BUILD_PROVIDER = "Only etro.gg or xivgear.app is supported."
    try:
        parsed_url = urlparse(job_build_url)
        netloc_elements = parsed_url.netloc.split(".")

        # etro.gg
        if all([n in netloc_elements for n in ["etro", "gg"]]):
            return True, "etro"
        # xivgear.app
        elif all([n in netloc_elements for n in ["xivgear", "app"]]):
            return True, "xivgear"
        else:
            return False, INVALID_BUILD_PROVIDER

        # invalid
    except Exception:
        return False, INVALID_BUILD_PROVIDER


def _is_valid_uuid(uuid_to_test, version=4) -> bool:
    """
    Check if uuid_to_test is a valid UUID.

     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def is_valid_domain(netloc, required_elements: list[str]) -> bool:
    """
    Check if the required domain elements are present in the given netloc.

    Args:
        netloc (str): The network location part of the URL (e.g., "xivgear.app").
        required_elements (list[str], optional): A list of required domain parts. Defaults to ["xivgear", "app"].

    Returns:
        bool: `True` if all required elements are present in the domain, otherwise `False`.
    """
    netloc_elements = netloc.split(".")
    return all([n in netloc_elements for n in required_elements])


def _parse_and_validate_etro_url(etro_url: str) -> tuple[Optional[str], str]:
    """
    Extract gearset ID from Etro URL and validate format.

    Args:
        etro_url: Full Etro gearset URL

    Returns:
        Tuple containing:
            - Gearset ID (UUID) if valid, None if invalid
            - Error message
    """
    error_code = None
    try:
        parts = urlparse(etro_url)
        if not is_valid_domain(parts.netloc, ["etro", "gg"]):
            return None, ERROR_CODE_MAP[1]

        gearset_id = [segment for segment in parts.path.split("/") if segment][-1]
        if not _is_valid_uuid(gearset_id):
            return None, ERROR_CODE_MAP[2]

    except Exception:
        gearset_id = None
        error_code = ERROR_CODE_MAP[3]

    return gearset_id, error_code


def _query_etro_stats(gearset_id: str) -> tuple[Union[dict[str, Any], str], bool]:
    """
    Query an Etro build given a gearset ID.

    Args:
        gearset_id (str): The UUID for the Etro gearset.

    Returns:
        Tuple[Union[dict[str, Any], str], bool]:
            - A tuple containing either the build result (dict) or an error message (str)
            - A boolean indicating success (True) or failure (False)
    """
    # Initialize a client & load the schema document
    client = coreapi.Client()
    schema = client.get("https://etro.gg/api/docs/")

    gearset_action = ["gearsets", "read"]
    gearset_params = {
        "id": gearset_id,
    }
    try:
        build_result = client.action(schema, gearset_action, params=gearset_params)
        return build_result, True

    except Exception as e:
        # TODO: write to DB or something
        return e.error.title, False


def _extract_etro_build_stats(
    build_result: dict[str, Any],
) -> tuple[str, str, str, int, int, int, int, int, int, Any, Union[str, int]]:
    """
    Extract build statistics from the Etro build result.

    Args:
        build_result (dict[str, Any]): The dictionary containing the Etro build data.

    Returns:
        Tuple[str, str, str, int, int, int, int, int, int, Any, Union[str, int]]:
            - Job abbreviation
            - Build name
            - Build role
            - Primary stat
            - Direct hit
            - Critical hit
            - Determination
            - Speed
            - Weapon Damage
            - Party bonus (type may vary from the API)
            - Tenacity (int if a Tank, otherwise "None")
    """
    job_abbreviated = build_result["jobAbbrev"]
    build_name = build_result["name"]

    build_role, main_stat_str, speed_stat_str = ETRO_JOB_STATS[job_abbreviated]

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

    return (
        job_abbreviated,
        build_name,
        build_role,
        primary_stat,
        dh,
        ch,
        determination,
        speed,
        wd,
        etro_party_bonus,
        secondary_stat,
    )


def etro_build(
    etro_url: str,
) -> tuple[
    bool,
    str,
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[int],
    Optional[float],
    Optional[str],
]:
    """Extract job build from an etro URL.

    Args:
        etro_url (str): URL to the etro.gg build.

    Returns:
        Tuple[bool, str, Optional[str], Optional[str], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[float], Optional[str]]:
            - Boolean indicating success or failure
            - Error message if any, empty string if no error
            - Build name
            - Build role
            - Primary stat
            - Determination
            - Speed
            - Critical hit
            - Direct hit
            - Weapon damage
            - Tenacity
            - Delay
            - Etro party bonus
    """
    invalid_return = [False, ""] + [None] * 11

    # Get ID from url
    gearset_id, error_message = _parse_and_validate_etro_url(etro_url)

    # Return problem with etro URL
    if error_message is not None:
        invalid_return[1] = error_message
        return tuple(invalid_return)

    build_result, etro_api_success = _query_etro_stats(gearset_id)

    if not etro_api_success:
        invalid_return[1] = build_result
        return tuple(invalid_return)

    (
        job_abbreviated,
        build_name,
        build_role,
        primary_stat,
        dh,
        ch,
        determination,
        speed,
        wd,
        etro_party_bonus,
        tenacity,
    ) = _extract_etro_build_stats(build_result)

    # TODO: Try to get by weapon ID
    delay = weapon_delays[job_abbreviated]

    return (
        True,
        "",
        build_name,
        build_role,
        primary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        tenacity,
        delay,
        etro_party_bonus,
    )


def _parse_and_validate_xiv_gear_url(
    xiv_gear_url: str,
) -> tuple[str, Optional[str], int]:
    """
    Extract and validate UUID and onlySetIndex from a given URL.

    Parameters
    ----------
    xiv_gear_url : str

    Returns
    -------
    Tuple[str, Optional[str], int]
        Tuple containing:
            - Error message if any, empty string if no error
            - Gearset ID if valid, None if invalid
            - Selected gearset index
    """
    error_message = ""
    try:
        parsed_url = urlparse(xiv_gear_url)
        query_params = parse_qs(parsed_url.query)

        if not is_valid_domain(parsed_url.netloc, ["xivgear", "app"]):
            return ERROR_CODE_MAP[1], None, 0

        # Extract the UUID from the 'page' parameter
        page_param = query_params.get("page", [None])[0]
        if page_param:
            id_candidate = page_param.split("|")
            # There are bis type sets that follow /bis/job/expansion/tier
            if "bis" in id_candidate:
                uuid_value = "/".join(id_candidate)
            # Otherwise the ID should be a uuid4
            elif _is_valid_uuid(id_candidate[-1]):
                uuid_value = id_candidate[-1]
            else:
                uuid_value = None
                error_message = ERROR_CODE_MAP[2]
        else:
            uuid_value = None
            error_message = ERROR_CODE_MAP[3]

        # Extract the onlySetIndex value
        set_index = int(
            query_params.get("onlySetIndex", query_params.get("selectedIndex", [-1]))[0]
        )

        return error_message, uuid_value, set_index
    except Exception:
        return ERROR_CODE_MAP[3], None, 0


def _query_xiv_gear_sets(xiv_gearset_id: str) -> tuple[str, Optional[list[dict]]]:
    """GET gearset information from xivgear API.

    Args:
        xiv_gearset_id (str): Gearset ID, either uuid4 or `/bis/{job}/{expansion}/{raid_tier}`

    Returns:
        Tuple[str, Optional[List[dict]]]
            - Error message if any, empty string if no error
            - List of gear sets if valid, None if invalid
    """
    request_url = f"https://api.xivgear.app/fulldata/{xiv_gearset_id}?partyBonus=0"
    xiv_gear_request = requests.get(request_url)
    try:
        xiv_gear_request.raise_for_status()
    except Exception as e:
        return str(e), None
    return "", xiv_gear_request.json()["sets"]


def _extract_xiv_gear_set(
    gear_set: list[dict],
) -> tuple[str, str, str, int, int, int, int, int, int, float, str]:
    """Extract the relevant job build stats from a xivgear build.

    Args:
        gear_set (dict): Dictionary containing gear set information.

    Returns:
        Tuple[str, str, str, int, int, int, int, int, int, float, str]
            - Job abbreviation
            - Build name
            - Build role
            - Primary stat
            - Direct hit
            - Critical hit
            - Determination
            - Speed
            - Weapon damage
            - Delay
            - Tenacity
    """
    XIV_GEAR_ROLE_MAP = {
        "Caster": "Magical Ranged",
        "Ranged": "Physical Ranged",
    }

    WD_SELECT = {
        "Magical Ranged": "wdMag",
        "Healer": "wdMag",
        "Tank": "wdPhys",
        "Melee": "wdPhys",
        "Physical Ranged": "wdPhys",
    }

    job_abbreviated = gear_set["computedStats"]["job"]
    build_role = gear_set["computedStats"]["jobStats"]["role"]
    build_role = XIV_GEAR_ROLE_MAP.get(build_role, build_role)
    main_stat_str = gear_set["computedStats"]["jobStats"]["mainStat"]

    # Determine the relevant speed stat (either "skillspeed" or "spellspeed")
    irrelevant_substats = set(
        gear_set["computedStats"]["jobStats"]["irrelevantSubstats"]
    )
    speed_stat = ({"skillspeed", "spellspeed"} - irrelevant_substats).pop()

    if "tenacity" in irrelevant_substats:
        tenacity = "None"
    else:
        tenacity = gear_set["computedStats"]["tenacity"]

    # Rest of the stats are simple dictionary calls
    build_name = gear_set["name"]
    primary_stat = gear_set["computedStats"][main_stat_str]
    dh = gear_set["computedStats"]["dhit"]
    ch = gear_set["computedStats"]["crit"]
    determination = gear_set["computedStats"]["determination"]
    speed = gear_set["computedStats"][speed_stat]
    wd = gear_set["computedStats"][WD_SELECT[build_role]]

    return (
        job_abbreviated,
        build_name,
        build_role,
        primary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        tenacity,
        1.0,
    )


def xiv_gear_build(xiv_gear_url: str) -> tuple[bool, str, Optional[list[Any]], int]:
    """Get build information from a xivgear.app link.

    Also extracts the selected page, if present.

    Args:
        xiv_gear_url (str): URL to xivgear.app sheet.

    Returns:
        Tuple[bool, str, Optional[List[Any]], int]
            - Boolean indicating success or failure
            - Error message if any, empty string if no error
            - List of extracted gear sets if successful, None if failed
            - Selected gear set index
    """
    error_message, xiv_gearset_id, gear_idx = _parse_and_validate_xiv_gear_url(
        xiv_gear_url
    )
    if error_message != "":
        return (False, error_message, None, 0)

    error_message, gear_sets = _query_xiv_gear_sets(xiv_gearset_id)
    if error_message != "":
        return (False, error_message, None, 0)

    return True, error_message, [_extract_xiv_gear_set(g) for g in gear_sets], gear_idx


if __name__ == "__main__":
    etro_id = "07ae7334-ca45-4333-9830-9b516658ae6d"

    _query_etro_stats(etro_id)
    error_code, gear_sets, gear_idx = xiv_gear_build(
        # "https://xivgear.app/?page=sl%7C01a73d6f-8f17-4aa5-acc8-a8f9ad911119" # PCT build
        # "https://xivgear.app/?page=sl%7Cf49f08b0-ce11-470f-a967-3e7613321213" # BRD build
        "https://xivgear.app/?page=sl%7C9ee61d69-7daa-41bd-9c28-8a0f0055f90f"  # DRK build
    )
    print(gear_idx)
