from typing import Any, Optional
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import coreapi
import requests

from crit_app.job_data.job_data import weapon_delays

JOB_STATS = {
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

def job_build_provider(job_build_url:str) -> bool:
    """Check if the required domain elements are present.

    Args:
        netloc (_type_): _description_
        required_elements (list[str], optional): _description_. Defaults to ["xivgear", "app"].

    Returns:
        bool: `True` if all required elements are present in the domain, otherwise `False`.
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
    """Check if the required domain elements are present.

    Args:
        netloc (_type_): _description_
        required_elements (list[str], optional): _description_. Defaults to ["xivgear", "app"].

    Returns:
        bool: `True` if all required elements are present in the domain, otherwise `False`.
    """
    netloc_elements = netloc.split(".")
    return all([n in netloc_elements for n in required_elements])


def _parse_and_validate_etro_url(etro_url: str) -> tuple[Optional[str], int]:
    """
    Extract gearset ID from Etro URL and validate format.

    Args:
        etro_url: Full Etro gearset URL

    Returns:
        Tuple containing:
            - Gearset ID (UUID) if valid, None if invalid
            - Error code:
                0 = Success
                1 = Invalid domain (not etro.gg)
                2 = Invalid UUID length
                3 = Query issue
    """
    error_code = 0
    try:
        parts = urlparse(etro_url)
        if not is_valid_domain(parts.netloc, ["etro", "gg"]):
            return None, 1

        gearset_id = [segment for segment in parts.path.split("/") if segment][-1]
        if not _is_valid_uuid(gearset_id):
            return None, 2

    except Exception:
        gearset_id = None
        error_code = 3

    return gearset_id, error_code


def _query_etro_stats(gearset_id: str):
    """Query etro build result given a gearset ID.

    Args:
        gearset_id (str): ID of the etro gearset

    Returns:
        _type_: _description_
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
        print(e.error.title)
        return e.error.title, False


def _extract_etro_build_stats(build_result):
    job_abbreviated = build_result["jobAbbrev"]
    build_name = build_result["name"]

    build_role, main_stat_str, speed_stat_str = JOB_STATS[job_abbreviated]

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


def etro_build(etro_url: str):
    """Extract job build from an etro URL.

    Args:
        etro_url (str): _description_

    Returns:
        _type_: _description_
    """
    invalid_return = [False, ""] + [None] * 11

    # Get ID from url
    gearset_id, error_code = _parse_and_validate_etro_url(etro_url)

    # Return problem with etro URL
    if error_code > 0:
        invalid_return[1] = ""
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
        secondary_stat,
    ) = _extract_etro_build_stats(build_result)

    # TODO: Try to get by weapon ID
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


def _parse_and_validate_xiv_gear_url(
    xiv_gear_url: str,
) -> tuple[int, Optional[str], int]:
    """
    Extract and validate UUID and onlySetIndex from a given URL.

    Parameters
    ----------
    url : str

    Returns
    -------
    Tuple containing:
        Tuple containing:
            - Error code:
                0 = Success
                1 = Invalid domain (not xivgear.app)
                2 = Invalid UUID length
                3 = Query issue
            - Gearset ID if valid, None if invalid
            - selected gearset ID
    """

    error_code = 0
    try:
        parsed_url = urlparse(xiv_gear_url)
        query_params = parse_qs(parsed_url.query)

        if not is_valid_domain(parsed_url.netloc, ["xivgear", "app"]):
            return 1, None, 0

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
                error_code = 0
            else:
                uuid_value = None
                error_code = 2
        else:
            uuid_value = None
            error_code = 2

        # Extract the onlySetIndex value
        set_index = int(query_params.get("onlySetIndex", query_params.get("selectedIndex", [0]))[0])

        return error_code, uuid_value, set_index
    except Exception:
        return 3, None, 0


def _query_xiv_gear_sets(xiv_gearset_id: str) -> tuple[int, Optional[list[dict]]]:
    """GET gearset information from xivgear API.

    Args:
        xiv_gearset_id (str): Gearset ID, either uuid4 or `/bis/{job}/{expansion}/{raid_tier}`

    Returns:
        Tuple[int, Optional[List[dict]]]
            - Error code:
                0 = Success
                1 = Invalid domain (not xivgear.app)
                2 = Invalid UUID length
                3 = Query issue
            - List of gear sets if valid, None if invalid
    """
    request_url = f"https://api.xivgear.app/fulldata/{xiv_gearset_id}?partyBonus=0"
    xiv_gear_request = requests.get(request_url)
    try:
        xiv_gear_request.raise_for_status()
    except Exception as e:
        return e.error.title, None
    return 0, xiv_gear_request.json()["sets"]


def _extract_xiv_gear_set(
    gear_set: list[dict],
) -> tuple[str, str, str, int, int, int, int, int, int, float, str]:
    """Extract the relevant job build stats from a xivgear build.

    Args:
        gear_set (list[dict]): _description_

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
    job_abbreviated = gear_set["computedStats"]["job"]
    build_role = gear_set["computedStats"]["jobStats"]["role"]
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
    wd = gear_set["computedStats"]["wdMag"]

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
        1.0,
        tenacity,
    )


def xiv_gear_build(xiv_gear_url: str) -> tuple[list[Any], int]:
    """Get build information from a xivgear.app link.

    Also extracts the selected page, if present.

    Args:
        xiv_gear_url (str): URL to xivgear.app sheet.

    Returns:
        Tuple[List[Any], int]
            - List of extracted gear sets
            - Selected gear set index
    """
    error_code, xiv_gearset_id, gear_idx = _parse_and_validate_xiv_gear_url(
        xiv_gear_url
    )
    if error_code > 0:
        return (error_code, None, 0)

    error_code, gear_sets = _query_xiv_gear_sets(xiv_gearset_id)
    if error_code != 0:
        return (error_code, None, 0)

    # FIXME: check if only one gear set is present, if it is,
    # return that and set gear_idx = 0
    return 0, [_extract_xiv_gear_set(g) for g in gear_sets], gear_idx


if __name__ == "__main__":
    etro_id = "07ae7334-ca45-4333-9830-9b516658ae6d"

    _query_etro_stats(etro_id)
    gear_sets, gear_idx = xiv_gear_build(
        "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
    )
    print(gear_idx)
