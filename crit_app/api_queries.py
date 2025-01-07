"""API queries made to FFLogs and Etro."""

import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests

from crit_app.config import FFLOGS_TOKEN
from crit_app.job_data.roles import role_mapping

# API config
url = "https://www.fflogs.com/api/v2/client"
api_key = FFLOGS_TOKEN  # or copy/paste your key here
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def parse_etro_url(etro_url: str) -> Tuple[Optional[str], int]:
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
                3 = Parse error

    Example:
        ```python
        # Valid URL
        gid, err = parse_etro_url("https://etro.gg/gearset/123e4567-e89b...")
        assert err == 0

        # Invalid domain
        gid, err = parse_etro_url("https://google.com")
        assert err == 1
        ```
    """
    error_code = 0
    try:
        parts = urlparse(etro_url)
        if parts.netloc != "etro.gg":
            return None, 1

        gearset_id = [segment for segment in parts.path.split("/") if segment][-1]
        if len(gearset_id) != 36:
            return None, 2

    except Exception:
        gearset_id = None
        error_code = 3

    return gearset_id, error_code


def parse_fflogs_url(fflogs_url: str) -> Tuple[Optional[str], Optional[int], int]:
    """
    Read the parts of an FFLogs URL to get report ID and fight ID.

    Returns an error code if an incorrect link is provided.

    Parameters:
        fflogs_url (str): The FFLogs URL to parse.

    Returns:
        tuple[Optional[str], Optional[int], int]: A tuple containing the report ID, fight ID, and an error code.
                                                Error codes:
                                                0 - No error
                                                1 - Site is not fflogs.com
                                                2 - Fight ID not specified
                                                3 - Invalid report ID
    """
    parts = urlparse(fflogs_url)

    error_code = 0

    # FFLogs sneakily switched from # to ? for fight ID
    # Need to try both
    try:
        fight_id = parse_qs(parts.fragment)["fight"][0]
        fight_id = int(fight_id)
    except (KeyError, ValueError):
        try:
            fight_id = parse_qs(parts.query)["fight"][0]
            fight_id = int(fight_id)
        except (KeyError, ValueError):
            fight_id = None
            error_code = 2

    if parts.netloc != "www.fflogs.com":
        error_code = 1

    report_id = [segment for segment in parts.path.split("/") if segment][-1]
    # Light check if report ID is valid
    if len(report_id) != 16:
        error_code = 3
    return report_id, fight_id, error_code


# TODO: can be split up into multiple functions later
def get_encounter_job_info(
    code: str, fight_id: int
) -> Tuple[int, int, List[Dict], List[Dict], float, str, int, int, Dict[str, Any]]:
    """
    Fetch encounter details and job information from FFLogs API.

    Args:
        code: FFLogs report code (e.g. "a1b2c3d4")
        fight_id: Fight ID within the report

    Returns:
        Tuple containing:
            - encounter_id: FFLogs encounter identifier
            - start_time: Fight start timestamp (ms)
            - jobs: List of player/job info dicts
            - limit_break: List of limit break usage dicts
            - fight_time: Duration in seconds
            - fight_name: Name of encounter
            - report_start_time: Report start timestamp (ms)
            - furthest_phase_index: Highest phase reached
            - raw_response: Complete API response

    Example:
        >>> info = get_encounter_job_info("a1b2c3d4", 1)
        >>> encounter_id, start_time, jobs, *_ = info
    """
    variables = {"code": code, "id": [fight_id]}

    json_payload = {
        "query": """
        query EncounterInfo($code: String!, $id: [Int!]) {
            reportData {
                report(code: $code) {
                    startTime
                    rankings(fightIDs: $id)
                    fights(fightIDs: $id, translate: true) {
                        encounterID
                        kill,
                        startTime,
                        endTime,
                        name,
                        lastPhase
                    }
                    playerDetails(fightIDs: $id)
                    table(fightIDs: $id, dataType: DamageDone)
                }
            }
        }
    """,
        "variables": variables,
        "operationName": "EncounterInfo",
    }
    r = requests.post(url=url, json=json_payload, headers=headers)
    r = json.loads(r.text)

    # Encounter info and whether kill happened
    encounter_info = r["data"]["reportData"]["report"]["fights"][0]
    encounter_id = encounter_info["encounterID"]
    start_time = encounter_info["startTime"]
    furthest_phase_index = encounter_info["lastPhase"]

    # This probably isn't needed, but would require updating a table schema.
    server_info = r["data"]["reportData"]["report"]["playerDetails"]["data"][
        "playerDetails"
    ]
    server_info = {y["name"]: y["server"] for x in server_info for y in server_info[x]}
    # simple filter and remapping
    jobs = []
    limit_break = []
    for x in r["data"]["reportData"]["report"]["table"]["data"]["entries"]:
        if "pets" in x.keys():
            pet_ids = json.dumps([y["id"] for y in x["pets"]])
        else:
            pet_ids = None
        # Only add players (not limit break)
        if x["name"] != "Limit Break":
            jobs.append(
                {
                    "job": x["icon"],
                    "player_name": x["name"],
                    "player_server": server_info[x["name"]],
                    "player_id": x["id"],
                    "pet_ids": pet_ids,
                    "role": role_mapping[x["icon"]],
                }
            )

        elif x["name"] == "Limit Break":
            limit_break.append(
                {
                    "job": x["icon"],
                    "player_name": x["name"],
                    "player_server": None,
                    "player_id": x["id"],
                    "pet_ids": pet_ids,
                    "role": "Limit Break",
                }
            )

    if len(r["data"]["reportData"]["report"]["rankings"]["data"]) == 0:
        fight_time = (
            r["data"]["reportData"]["report"]["fights"][0]["endTime"]
            - r["data"]["reportData"]["report"]["fights"][0]["startTime"]
        )
    else:
        fight_time = r["data"]["reportData"]["report"]["rankings"]["data"][0][
            "duration"
        ]
    fight_name = r["data"]["reportData"]["report"]["fights"][0]["name"]
    report_start_time = r["data"]["reportData"]["report"]["startTime"]
    return (
        encounter_id,
        start_time,
        jobs,
        limit_break,
        fight_time / 1000,
        fight_name,
        report_start_time,
        furthest_phase_index,
        r,
    )


def limit_break_damage_events(
    report_id: str, fight_id: int, limit_break_id: int, phase=None
) -> pd.DataFrame:
    """
    Get all limit break damage events that successfully landed on targets.

    Args:
        report_id: FFLogs report identifier (e.g. "a1b2c3d4")
        fight_id: Fight ID within the report
        limit_break_id: Actor ID for limit break

    Returns:
        DataFrame containing damage events with columns:
            - report_id: Original report ID
            - fight_id: Fight identifier
            - timestamp: Event timestamp (ms)
            - target_id: Target actor ID
            - amount: Damage amount

    Example:
        >>> events = limit_break_damage_events("a1b2c3", 1, 16)
        >>> print(events.head())
           report_id  fight_id  timestamp  target_id  amount
        0    a1b2c3         1  12345678        101   50000
    """
    if (phase is None) or (phase == 0):
        filter_slug = ""
    else:
        filter_slug = f"encounterPhase={phase}"

    variables = {
        "code": report_id,
        "id": [fight_id],
        "limitBreakID": limit_break_id,
        "filterSlug": filter_slug,
    }

    json_payload = {
        "query": """
            query LimitBreakDamage(
                $code: String!
                $id: [Int]!
                $limitBreakID: Int!
                $filterSlug: String!
            ) {
                reportData {
                    report(code: $code) {
                        startTime
                        events(
                            fightIDs: $id
                            sourceClass: "LimitBreak"
                            sourceID: $limitBreakID
                            filterExpression: $filterSlug
                        ) {
                            data
                        }
                    }
                }
            }
    """,
        "variables": variables,
        "operationName": "LimitBreakDamage",
    }
    r = requests.post(url=url, json=json_payload, headers=headers)
    r = json.loads(r.text)

    start_time = lb_data = r["data"]["reportData"]["report"]["startTime"]
    lb_data = r["data"]["reportData"]["report"]["events"]["data"]

    if len(lb_data) == 0:
        return pd.DataFrame(
            data=[],
            columns=["report_id", "fight_id", "timestamp", "target_id", "amount"],
        )
    else:
        lb_df = pd.DataFrame(lb_data).rename(columns={"targetID": "target_id"})
        lb_df = lb_df[lb_df["type"] == "calculateddamage"]

        if "unpaired" in lb_df:
            lb_df[lb_df["unpaired"] != True]

        lb_df["fight_id"] = fight_id
        lb_df["report_id"] = report_id
        lb_df = lb_df[["report_id", "fight_id", "timestamp", "target_id", "amount"]]
        lb_df["timestamp"] += start_time
        return lb_df


if __name__ == "__main__":
    limit_break_damage_events("ZfnF8AqRaBbzxW3w", 5, 56, 5)
