"""Fetch and process FFLogs encounter data."""

from pathlib import Path

from pydantic import AnyHttpUrl, ValidationError

from crit_app_v2.fflogs_encounters.client import query_report
from crit_app_v2.fflogs_encounters.errors import FFLogsError, FFLogsErrorCategory
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
    FFLogsEncounterReport,
    FFLogsReportFightData,
)
from crit_app_v2.game_data import JOB_SPECS
from crit_app_v2.game_data.encounters import get_excluded_enemy_ids
from crit_app_v2.game_data.jobs import Job

_LAST_FIGHT_ID_QUERY = (
    Path(__file__).parent / "queries" / "LastFightID.gql"
).read_text(encoding="utf-8")

_ENCOUNTER_INFO_QUERY = (
    Path(__file__).parent / "queries" / "EncounterInfo.gql"
).read_text(encoding="utf-8")


def _query_last_fight_id(report_id: str) -> int:
    """Find the ID of the latest-started fight in an FFLogs report.

    In-progress fights are included. When multiple fights have the same start
    time, the fight with the greatest ID is selected for deterministic results.

    Parameters
    ----------
    report_id
        FFLogs report code to query.

    Returns
    -------
    int
        The selected fight ID.

    Raises
    ------
    FFLogsError
        If the request fails, the report is unavailable, no fights are present,
        or FFLogs returns an error or invalid response.
    """
    report = query_report(
        _LAST_FIGHT_ID_QUERY,
        variables={"code": report_id},
        operation_name="LastFightID",
    )

    try:
        fight_list = FFLogsReportFightData.model_validate(report)
    except ValidationError as error:
        raise FFLogsError(
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
            detail="FFLogs report did not contain valid fight data.",
        ) from error

    if not fight_list.fights:
        raise FFLogsError(FFLogsErrorCategory.NO_FIGHTS)

    latest_fight = max(
        fight_list.fights,
        key=lambda fight: (fight.start_time, fight.id),
    )
    return latest_fight.id


def _query_encounter_info(
    encounter_url: EncounterUrl, resolved_fight_id: int
) -> Encounter:
    """Fetch and normalize encounter data for a single fight.

    Parameters
    ----------
    encounter_url
        Validated URL the fight was requested from.
    fight_id
        Resolved numeric fight ID.

    Returns
    -------
    Encounter
        Normalized encounter and participant data.

    Raises
    ------
    FFLogsError
        If the request fails, the fight is not found, or FFLogs returns an
        invalid response.
    """

    report = query_report(
        _ENCOUNTER_INFO_QUERY,
        variables={"code": encounter_url.report_id, "id": resolved_fight_id},
        operation_name="EncounterInfo",
    )

    try:
        report_data = FFLogsEncounterReport.model_validate(report)
    except ValidationError as error:
        raise FFLogsError(
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
            detail="FFLogs report did not contain valid encounter data.",
        ) from error

    if not report_data.fights:
        raise FFLogsError(FFLogsErrorCategory.NO_FIGHTS)

    encounter = report_data.fights[0]
    players = report_data.player_details

    enemy_npcs = [npc for npc in encounter.enemy_npcs or [] if npc is not None]
    friendly_pets = [pet for pet in encounter.friendly_pets or [] if pet is not None]

    excluded_enemy_ids = get_excluded_enemy_ids(
        encounter.encounter_id,
        [(npc.game_id, npc.id) for npc in enemy_npcs],
    )

    # Prefer combat time; fall back to wall-clock duration.
    kill_time = (
        encounter.combat_time
        if encounter.combat_time
        else encounter.end_time - encounter.start_time
    ) / 1000

    personnel_list: list[EncounterPersonnel] = []
    for pl_role in (players.healers, players.tanks, players.dps):
        for pl in pl_role or []:
            try:
                job = Job(pl.job)
            except ValueError as error:
                raise FFLogsError(
                    FFLogsErrorCategory.UNEXPECTED_RESPONSE,
                    detail=f"Unknown job {pl.job!r} in FFLogs player details.",
                ) from error

            pet_ids = [
                pet.id
                for pet in friendly_pets
                if pet.id is not None and pet.pet_owner == pl.id
            ]
            personnel_list.append(
                EncounterPersonnel(
                    player_name=pl.name,
                    player_server=pl.server,
                    player_id=pl.id,
                    pet_ids=pet_ids,
                    job=job,
                    role=JOB_SPECS[job].role,
                )
            )

    return Encounter(
        encounter_url=encounter_url,
        fight_id_resolved=resolved_fight_id,
        encounter_id=encounter.encounter_id,
        encounter_name=encounter.name,
        last_phase_index=encounter.last_phase,
        kill_time=kill_time,
        excluded_enemy_ids=excluded_enemy_ids,
        players=personnel_list,
        limit_break=None,
    )


def fetch_encounter(raw_url: str) -> Encounter:
    """Validate an FFLogs URL and fetch its encounter data.

    A ``fight=last`` URL is resolved to the latest fight, and the returned
    encounter links to the resolved fight ID.

    Parameters
    ----------
    raw_url
        User-entered FFLogs report URL.

    Returns
    -------
    Encounter
        Normalized encounter and participant data.

    Raises
    ------
    FFLogsError
        If the URL is invalid, the request fails, or FFLogs returns an
        unavailable report or invalid response.
    """
    try:
        encounter_url = EncounterUrl(build_url=AnyHttpUrl(raw_url.strip()))
    except ValidationError as error:
        raise FFLogsError(FFLogsErrorCategory.INVALID_URL, detail=str(error)) from error

    fight_id = encounter_url.fight_id
    if fight_id == "last":
        fight_id = _query_last_fight_id(encounter_url.report_id)

    return _query_encounter_info(encounter_url.with_fight_id(fight_id), fight_id)


if __name__ == "__main__":
    print(fetch_encounter("https://www.fflogs.com/reports/CFYTJZDQG7mMKL4w?fight=last"))
