import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from crit_app.config import FFLOGS_TOKEN
from crit_app.job_data.encounter_data import excluded_enemy_game_ids
from crit_app.job_data.roles import role_mapping

# API config
url = "https://www.fflogs.com/api/v2/client"
api_key = FFLOGS_TOKEN  # or copy/paste your key here
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

FFLOGS_ERROR_MAPPING = {
    0: "URL isn't fflogs.",
    1: "A specific fight must be linked, ?fight={fightID} or ?fight=last.",
    2: "No report ID found.",
}


def _fflogs_report_id(url_path: str) -> tuple[str | None]:
    """Get the report ID from an FFLogs URL.

    Requires "report" to be present and the ID to be 16 elements long.

    Args:
        url_path (str): Path query from urlparse.

    Returns:
        tuple[str | None]: Report ID if present, or None if not.
    """
    report_parts: list = [segment for segment in url_path.split("/") if segment]

    if len(report_parts) != 2:
        return None

    if report_parts[0] != "reports":
        return None

    if len(report_parts[1]) != 16:
        return None

    return report_parts[1]


def _fflogs_fight_id(url_query: dict[list] | None) -> int | str | None:
    """Extract the fight ID from an fflogs URL.

    Args:
        url_query (dict[list] | None): URL query dictionary from urlparse.

    Returns:
        int | str | None: Fight ID, either an int or "last".
    """
    fight_list = url_query.get("fight")
    if fight_list is not None:
        # Check that something is actually there.
        if len(fight_list) == 0:
            return None
        # Allow fight=last
        if fight_list[0] == "last":
            return fight_list[0]
        try:
            fight_id = int(fight_list[0])
            return fight_id
        except ValueError:
            return None
    else:
        return None


def parse_fflogs_url(fflogs_url: str) -> tuple[str | None, int | None, str]:
    """Read the parts of an FFLogs URL to get report ID, fight ID, and error, if one occurred.

    Args:
        fflogs_url (str): Link to FFLogs fight.

    Returns:
        tuple[str | None, int | None, str]: report ID, fight ID, and error (no error is "").
    """
    # FFLogs sneakily switched from # to ? for fight ID
    fflogs_url = fflogs_url.replace("#", "?")
    parts = urlparse(fflogs_url)

    # Check domain
    if parts.netloc != "www.fflogs.com":
        return None, None, FFLOGS_ERROR_MAPPING[0]

    # Check fight ID
    fight_id = _fflogs_fight_id(parse_qs(parts.query))
    if fight_id is None:
        return None, None, FFLOGS_ERROR_MAPPING[1]

    # Check report
    report_id = _fflogs_report_id(parts.path)
    if report_id is None:
        return None, None, FFLOGS_ERROR_MAPPING[2]

    return report_id, fight_id, ""


def _encounter_query_error_messages(response: dict) -> str:
    """Check if the response contains an error key.

    Return the error message if so.

    Args:
        response (dict): FFLogs query response.

    Returns:
        str: Error message, "" means no error.
    """
    if "errors" in response.keys():
        try:
            error_message = response["errors"][0].get(
                "message", "Error getting encounter info."
            )
            if error_message == "You do not have permission to view this report.":
                return "Linked report is private/no longer available."
            return response["errors"][0].get("message", "Error getting encounter info.")
        except Exception as e:
            str(e)

    return ""


def _encounter_query_fight_id_exists(response_dict: dict) -> bool:
    """Check if the fight ID actually exists.

    Args:
        response_dict (dict): EncounterInfo query response.

    Returns:
        bool: Fight ID exists (True) | fight ID doesn't (False)
    """
    try:
        return len(response_dict["data"]["reportData"]["report"]["fights"]) > 0
    except KeyError:
        return False


def _query_last_fight_id(report_id: str) -> tuple[int, str]:
    """
    Find the numerical Fight ID when fight=last is passed in.

    Defaults to 0 if unsuccessful.
    This seems to be the number of fights with an end time.

    It doesn't seem like exportedSegments or segments always equals that value.
    """

    variables = {"code": report_id}
    json_payload = {
        "query": """
    query LastFightID($code: String!) {
        reportData {
            report(code: $code) {
                segments,
                startTime,
                exportedSegments,
                fights{
                    endTime
                }
            }
        }
    }
    """,
        "variables": variables,
        "operationName": "LastFightID",
    }
    r = requests.post(url=url, json=json_payload, headers=headers)
    r.raise_for_status()

    response = r.json()
    query_errors = _encounter_query_error_messages(response)

    if query_errors != "":
        return 0, query_errors

    try:
        return len(response["data"]["reportData"]["report"].get("fights", [])), ""

    except Exception as e:
        return 0, str(e)


def _query_encounter_info(
    report_id: str, fight_id: int | str, headers: dict[str, str] = headers
) -> tuple[dict[str, Any], str]:
    """Query FFLogs for encounter information."""
    error_message = ""

    variables = {"code": report_id, "id": [fight_id]}
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
                        enemyNPCs{
                            gameID,
                            id
                        }
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
    r.raise_for_status()
    response_dict = r.json()

    _encounter_query_error_messages(response_dict)
    if not _encounter_query_fight_id_exists(response_dict):
        error_message = f"fight={fight_id} does not exist"

    return response_dict, error_message


def _excluded_enemy_ids(
    encounter_info: dict, encounter_id: int, excluded_enemy_game_ids: dict
) -> list[int] | None:
    """Figure out the report IDs of certain enemies based off their.

    game ID. Damage to these enemies are excluded.

    Example: Damage to Dark Crystals in FRU should be excluded.

    Args:
        encounter_info (dict): Encounter info portion of the FFLogs API response
        encounter_id (int): Encounter ID, used to figure out which Game IDs to use.

    Returns:
        list[int] | None: List of enemy IDs if any are present, or None if not.
    """
    excluded_enemy_ids = None

    if encounter_id in excluded_enemy_game_ids.keys():
        potential_exclusions = [
            e["id"]
            for e in encounter_info["enemyNPCs"]
            if e["gameID"] in excluded_enemy_game_ids[encounter_id]
        ]
        if potential_exclusions:
            excluded_enemy_ids = potential_exclusions
    return excluded_enemy_ids


def _encounter_duration(response: dict) -> float:
    """Get the duration of the encounter in seconds.

    There was a point where
    `end time` - `start time` was different from the ranking duration, but
    that appears to be resolved.

    Args:
        response (dict): FFLogs encounter API response.

    Returns:
        float: Duration of the encounter in seconds.
    """
    if len(response["data"]["reportData"]["report"]["rankings"]["data"]) == 0:
        fight_time = (
            response["data"]["reportData"]["report"]["fights"][0]["endTime"]
            - response["data"]["reportData"]["report"]["fights"][0]["startTime"]
        )
    else:
        fight_time = response["data"]["reportData"]["report"]["rankings"]["data"][0][
            "duration"
        ]
    return fight_time / 1000


def _player_server_data(response: dict):
    server_info = response["data"]["reportData"]["report"]["playerDetails"]["data"][
        "playerDetails"
    ]
    return {y["name"]: y["server"] for x in server_info for y in server_info[x]}


def _encounter_jobs_and_lb(response: dict) -> tuple[list[dict], list[dict]]:
    """Process player job information and LB ID information.

    Args:
        player_entries (dict): _description_
        player_server_info (dict): _description_

    Returns:
        tuple[list[dict], list[dict]]:
            A tuple containing two lists:
              1) jobs (list of dict): Each dictionary includes player's job icon, name, server name,
                 ID, any pet IDs, and role mapping.
              2) limit_break (list of dict): Equivalent dictionaries specifically for the "Limit Break" entry.
    """
    player_server_info = _player_server_data(response)

    jobs = []
    limit_break = []
    for x in response["data"]["reportData"]["report"]["table"]["data"]["entries"]:
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
                    "player_server": player_server_info[x["name"]],
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
    return jobs, limit_break


def encounter_information(
    report_id: str, fight_id: int | str
) -> tuple[
    str,  # error_message
    int,  # fight_id
    int,  # encounter_id
    int,  # start_time
    list[dict[str, Any]],  # jobs
    list[dict[str, Any]],  # limit_break
    float,  # fight_time in seconds
    str,  # fight_name
    int,  # report_start_time
    int,  # furthest_phase_index
    list[int],  # excluded_enemy_ids
]:
    """
    Retrieve essential information for a given FFLogs encounter.

    If fight_id is "last", it first looks up the last fight's numeric ID. It
    then queries the FFLogs API to gather the following details:
      • encounter ID
      • fight start time
      • job details (players, pets, etc.)
      • limit break info
      • fight duration
      • encounter name
      • FFLogs report start time
      • furthest phase index reached
      • IDs of excluded enemies (if any)

    If an error occurs or the fight is not found, an error message is returned along
    with None in place of the other values.

    Args:
        report_id (str): The FFLogs report ID string (16 chars).
        fight_id (Union[int, str]): The fight ID or "last" to request the final fight.

    Returns:
        Tuple[str, Optional[int], Optional[int], Optional[int], Optional[List[Dict[str, Any]]],
        Optional[List[Dict[str, Any]]], Optional[float], Optional[str], Optional[int],
        Optional[int], Optional[List[int]]]:
            A tuple containing:
              1) An error message (str) or empty string if none.
              2) The resolved fight ID (int) or None if invalid.
              3) The encounter ID (int) or None.
              4) The fight start time (int) or None.
              5) A list of job dictionaries (or None if unavailable).
              6) A list of limit break dictionaries (or None).
              7) The fight duration in seconds (float) or None.
              8) The fight name (str) or None.
              9) The report start time (int) or None.
              10) The furthest phase index (int) or None.
              11) A list of excluded enemy IDs (or None).
    """
    # Find the actual ID of what fight=last is
    if fight_id == "last":
        fight_id, error_message = _query_last_fight_id(report_id)
        if (fight_id == 0) | (error_message != ""):
            return (
                error_message,
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
    # Do the actual query now that the true fight ID is known
    r, error_message = _query_encounter_info(report_id, fight_id)

    if error_message != "":
        return (
            error_message,
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
    # Encounter info and whether kill happened
    encounter_info = r["data"]["reportData"]["report"]["fights"][0]
    encounter_id = encounter_info["encounterID"]
    start_time = encounter_info["startTime"]
    furthest_phase_index = encounter_info["lastPhase"]
    fight_name = r["data"]["reportData"]["report"]["fights"][0]["name"]
    report_start_time = r["data"]["reportData"]["report"]["startTime"]

    # More involved encounter info
    jobs, limit_break = _encounter_jobs_and_lb(r)
    excluded_enemy_ids = _excluded_enemy_ids(
        encounter_info, encounter_id, excluded_enemy_game_ids
    )
    fight_time = _encounter_duration(r)

    return (
        error_message,
        fight_id,
        encounter_id,
        start_time,
        jobs,
        limit_break,
        fight_time,
        fight_name,
        report_start_time,
        furthest_phase_index,
        excluded_enemy_ids,
    )


if __name__ == "__main__":
    # print(
    #     # parse_fflogs_url("https://www.fflogs.com/reports/qrAnckMdyD68xzZN?fight=last")
    #     parse_fflogs_url("https://www.fflogs.com/reports/qrAnckMdyD68xzZN")
    # )
    # _query_encounter_info("qrAnckMdyD68xzZN", 100)
    encounter_information("qrAnckMdyD68xzZN", 3)
    # encounter_information("PFAWB3trqYNV1ZdX", 3)
    # response = {
    #     "errors": [
    #         {
    #             "message": "You do not have permission to view this report.",
    #             "extensions": {"category": "graphql"},
    #             "locations": [{"line": 3, "column": 3}],
    #             "path": ["reportData", "report"],
    #         }
    #     ],
    #     "data": {"reportData": {"report": None}},
    # }

    # _encounter_query_error_messages(response)
