"""
API queries made to FFLogs and Etro.
"""

import json
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests

from crit_app.config import FFLOGS_TOKEN
from crit_app.job_data.roles import role_mapping

# API config
url = "https://www.fflogs.com/api/v2/client"
api_key = FFLOGS_TOKEN  # or copy/paste your key here
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def parse_etro_url(etro_url: str):
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


def parse_fflogs_url(fflogs_url: str):
    """
    Read the parts of an FFLogs URL to get report ID and fight ID.
    Returns and error code if an incorrect link is returned.

    Returns:
    report_id - string of the report ID
    fight_id - int of the fight ID
    error_code - 0: no error; 1: site is not fflogs.com; 2: fight ID not specified, 3: invalid report ID
    """
    parts = urlparse(fflogs_url)

    error_code = 0

    try:
        fight_id = parse_qs(parts.fragment)["fight"][0]
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


def get_encounter_job_info(code: str, fight_id: int):
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
                        name
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
        r,
    )


def limit_break_damage_events(report_id: str, fight_id: int, limit_break_id: int):
    """
    Get all LB damage events which successfully landed on its target as a pandas DataFrame.
    """
    variables = {"code": report_id, "id": [fight_id], "limitBreakID": limit_break_id}

    json_payload = {
        "query": """
        query LimitBreakDamage($code: String!, $id: [Int]!, $limitBreakID: Int!) {
            reportData {
                report(code: $code) {
                    startTime
                    events(fightIDs: $id, sourceClass:"LimitBreak", sourceID: $limitBreakID){
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


def boss_healing_amount(report_id: str, fight_id: int):
    """Get boss healing events, which affects total HP/damage dealt.
    Used for party analysis.

    Args:
        report_id (str): FFLogs report ID
        fight_id (int): FFLogs fight ID
    """

    variables = {"code": report_id, "id": [fight_id]}

    json_payload = {
        "query": """
            query bossHealing($code: String!, $id: [Int]!) {
                reportData {
                    report(code: $code) {
                        startTime
                        table(dataType: Healing, fightIDs: $id, hostilityType: Enemies)
                    }
                }
            }
    """,
        "variables": variables,
        "operationName": "bossHealing",
    }
    r = requests.post(url=url, json=json_payload, headers=headers)
    r = json.loads(r.text)

    healing_amount = r["data"]["reportData"]["report"]["table"]["data"]["entries"]
    if len(healing_amount) == 0:
        return 0
    else:
        return sum([h["total"] for h in healing_amount])
