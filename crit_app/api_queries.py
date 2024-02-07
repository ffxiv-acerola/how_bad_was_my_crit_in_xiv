"""
API queries made to FFLogs and Etro.
"""

from urllib.parse import urlparse, parse_qs
import json
import time

import requests

# from crit_app.config import FFLOGS_TOKEN
from config import FFLOGS_TOKEN

# API config
url = "https://www.fflogs.com/api/v2/client"
api_key = FFLOGS_TOKEN  # or copy/paste your key here
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def parse_etro_url(etro_url: str):
    error_code = 0
    try:
        parts = urlparse(etro_url)
        gearset_id = [segment for segment in parts.path.split("/") if segment][-1]

        if parts.netloc != "etro.gg":
            error_code = 1
        if len(gearset_id) != 36:
            error_code = 2
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
    except KeyError:
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
    # kill = encounter_info['kill']
    # TODO: Might need to keep longitudinal record of action potencies, which would involve start time
    start_time = encounter_info["startTime"]

    # Job info, only use healers for now
    healers = r["data"]["reportData"]["report"]["playerDetails"]["data"][
        "playerDetails"
    ]["healers"]
    # tanks = json.loads(r.text)['data']['reportData']['report']['playerDetails']['data']['playerDetails']['dps']
    # dps = json.loads(r.text)['data']['reportData']['report']['playerDetails']['data']['playerDetails']['tanks']

    healer_jobs = {x["icon"]: x["name"] for x in healers}
    # simple filter and remapping
    healer_jobs = [
        {
            "job": x["icon"],
            "player_name": x["name"],
            "player_server": x["server"],
            "player_id": x["id"],
        }
        for x in healers
    ]
    # tank_jobs = {x['icon']: x['name'] for x in tanks}
    # dps_jobs = {x['icon']: x['name'] for x in dps}

    fight_time = r["data"]["reportData"]["report"]["table"]["data"]["totalTime"]

    fight_name = r["data"]["reportData"]["report"]["fights"][0]["name"]

    return encounter_id, start_time, healer_jobs, fight_time / 1000, fight_name, r


def damage_events(fight_code, fight_id, job, start_time=0, end_time=int(time.time())):
    actions = []
    query = """
            query DpsActions(
                $code: String!
                $id: [Int]!
                $job: String!
                $endTime: Float!
                $startTime: Float!
            ) {
                reportData {
                    report(code: $code) {
                        events(
                            fightIDs: $id
                            startTime: $startTime
                            endTime: $endTime
                            dataType: DamageDone
                            sourceClass: $job
                            viewOptions: 1
                        ) {
                            data
                            nextPageTimestamp
                        }
                        table(fightIDs: $id, dataType: DamageDone)
                        fights(fightIDs: $id, translate: true) {
                            encounterID
                            kill,
                            startTime,
                            endTime,
                            name
                        }
                    }
                }
            }
    """
    # Initial query that gets the fight duration
    variables = {
        "code": fight_code,
        "id": [fight_id],
        "job": job,
        "startTime": start_time,
        "endTime": end_time,
    }
    json_payload = {
        "query": query,
        "variables": variables,
        "operationName": "DpsActions",
    }
    r = requests.post(url=url, json=json_payload, headers=headers)
    r = json.loads(r.text)
    next_timestamp = r["data"]["reportData"]["report"]["events"]["nextPageTimestamp"]
    actions.extend(r["data"]["reportData"]["report"]["events"]["data"])

    # Then remove that because damage done table and fight table doesn't need to be queried for every new page.
    # There might be a more elegant way to do this, but this is good enough.
    query = """
            query DpsActions(
                $code: String!
                $id: [Int]!
                $job: String!
                $endTime: Float!
                $startTime: Float!
            ) {
                reportData {
                    report(code: $code) {
                        events(
                            fightIDs: $id
                            startTime: $startTime
                            endTime: $endTime
                            dataType: DamageDone
                            sourceClass: $job
                            viewOptions: 1
                        ) {
                            data
                            nextPageTimestamp
                        }
                    }
                }
            }
            """
    variables = {
        "code": fight_code,
        "id": [fight_id],
        "job": job,
        "startTime": next_timestamp,
        "endTime": end_time,
    }

    # Get fight time by subtracting downtime from the total time
    # Downtime wont exist as a key if there is no downtime, so a try/except is needed.
    fight_time = r["data"]["reportData"]["report"]["table"]["data"]["totalTime"]
    try:
        downtime = r["data"]["reportData"]["report"]["table"]["data"]["downtime"]
    except KeyError:
        downtime = 0

    fight_time = (fight_time - downtime) / 1000
    fight_name = r["data"]["reportData"]["report"]["fights"][0]["name"]
    # Loop until no more pages
    while next_timestamp is not None:
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "DpsActions",
        }

        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)
        next_timestamp = r["data"]["reportData"]["report"]["events"][
            "nextPageTimestamp"
        ]
        actions.extend(r["data"]["reportData"]["report"]["events"]["data"])
        variables = {
            "code": fight_code,
            "id": [fight_id],
            "job": job,
            "startTime": next_timestamp,
            "endTime": end_time,
        }
        print(variables)

    return actions, fight_time, fight_name
