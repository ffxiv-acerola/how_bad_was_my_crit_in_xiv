"""Fetch XIVGear build data and transform sets into role-level models."""

from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import requests
from pydantic import AnyHttpUrl

from crit_app_v2.build_providers.errors import BuildErrorCategory, BuildProviderError
from crit_app_v2.build_providers.models import (
    BuildProvider,
    BuildUrl,
    LoadedXivGearBuild,
    RoleBuildStatsModel,
)
from crit_app_v2.build_providers.models.xivgear_models import LoadedXivGearSet
from crit_app_v2.game_data.jobs import JOB_SPECS, Job
from crit_app_v2.game_data.roles import ROLE_SPECS, Role
from crit_app_v2.game_data.stats import MAIN_STAT_SPEC, SPEED_STAT_SPEC

_WEAPON_DAMAGE_STAT_BY_ROLE = {
    Role.TANK: "wdPhys",
    Role.HEALER: "wdMag",
    Role.MELEE: "wdPhys",
    Role.PHYSICAL_RANGED: "wdPhys",
    Role.MAGICAL_RANGED: "wdMag",
}


def _validate_recognized_xiv_gear_link(raw_url: AnyHttpUrl) -> None:
    """Validate UUIDs in known single-job XIVGear link formats.

    Other XIVGear routes, including BiS pages, are left to XIVGear to process.
    """
    parsed_url = urlsplit(str(raw_url))
    page_values = parse_qs(parsed_url.query, keep_blank_values=True).get("page", [])

    identifiers: list[str] = []
    for page in page_values:
        if page.startswith("sl|"):
            identifiers.append(page.removeprefix("sl|"))

    path_parts = [part for part in parsed_url.path.split("/") if part]
    if len(path_parts) == 2 and path_parts[0] in {"sl", "share"}:
        identifiers.append(path_parts[1])

    fragment_parts = [part for part in parsed_url.fragment.split("/") if part]
    if len(fragment_parts) == 2 and fragment_parts[0] == "sl":
        identifiers.append(fragment_parts[1])

    for identifier in identifiers:
        try:
            UUID(identifier)
        except ValueError as error:
            raise BuildProviderError(
                BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
            ) from error


def _query_xiv_gear_sets(raw_url: AnyHttpUrl) -> dict[str, Any]:
    """Fetch full gearset data for a user-provided XIVGear URL.

    Parameters
    ----------
    raw_url
        Full XIVGear URL. It is passed to the API intact so supported URL
        routes and query parameters remain under XIVGear's control.

    Returns
    -------
    dict[str, Any]
        Full response from the XIVGear ``fulldata`` endpoint.
    """
    response = requests.get(
        "https://api.xivgear.app/fulldata",
        params={
            "url": str(raw_url),
            "partyBonus": 0,
        },
        headers={"User-Agent": "how-bad-was-my-crit-in-xiv/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _gearset_index(raw_url: AnyHttpUrl, response: dict[str, Any]) -> int | None:
    """Resolve the selected set's index in the API response.

    A response containing one set represents a selected set, including when
    the URL uses ``onlySetIndex``. Otherwise, ``selectedIndex`` in the URL is
    interpreted against the response's ``sets`` list.

    Parameters
    ----------
    raw_url
        Full user-provided XIVGear URL.
    response
        Full API response containing a ``sets`` list.

    Returns
    -------
    int or None
        Selected response index, or ``None`` when the URL selects no set.

    Raises
    ------
    BuildProviderError
        If the selected index is malformed, out of range, or points to a
        separator rather than a gear set.
    """
    sets = response["sets"]
    if len(sets) == 1:
        if sets[0].get("isSeparator", False):
            raise BuildProviderError(
                BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
            )
        return 0

    query = parse_qs(urlsplit(str(raw_url)).query)
    selected_index_values = query.get("selectedIndex")
    if not selected_index_values:
        return None

    try:
        index = int(selected_index_values[0])
    except (TypeError, ValueError) as error:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        ) from error

    if not 0 <= index < len(sets):
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        )
    if sets[index].get("isSeparator", False):
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        )

    return index


def _process_xiv_gear_set(
    gear_set: dict[str, Any], response_index: int
) -> tuple[Role, LoadedXivGearSet]:
    """Normalize one non-separator set from the XIVGear response.

    Parameters
    ----------
    gear_set
        One entry from the API response's ``sets`` list.
    response_index
        This entry's original index in that list.

    Returns
    -------
    tuple[Role, LoadedXivGearSet]
        The set's role and normalized name, stats, and response index.
    """
    computed_stats = gear_set["computedStats"]
    job = Job(computed_stats["job"])
    job_spec = JOB_SPECS[job]
    role = job_spec.role
    role_spec = ROLE_SPECS[role]

    tenacity = computed_stats["tenacity"] if role_spec.requires_tenacity else None
    stats = RoleBuildStatsModel(
        main_stat=computed_stats[MAIN_STAT_SPEC[job_spec.main_stat].xivgear_name],
        determination=computed_stats["determination"],
        speed_stat=computed_stats[SPEED_STAT_SPEC[role_spec.speed_stat].xivgear_name],
        critical_hit=computed_stats["crit"],
        direct_hit=computed_stats["dhit"],
        weapon_damage=computed_stats[_WEAPON_DAMAGE_STAT_BY_ROLE[role]],
        tenacity=tenacity,
    )

    return role, LoadedXivGearSet(
        response_index=response_index,
        build_name=gear_set["name"],
        build_stats=stats,
    )


def load_xiv_gear_build(build_url: BuildUrl) -> LoadedXivGearBuild:
    """Fetch and normalize all usable sets from an XIVGear URL.

    Set jobs are used internally to calculate their role-specific stats. The
    loaded result exposes the role, not the individual jobs.

    Parameters
    ----------
    build_url
        Validated URL classified as an XIVGear URL.

    Returns
    -------
    LoadedXivGearBuild
        Normalized sets, their response indexes, the URL-selected index, and
        the role shared by the usable sets.

    Raises
    ------
    BuildProviderError
        If the URL is not classified as XIVGear, the selection is invalid, or
        the sheet contains no usable sets or multiple roles.
    requests.HTTPError
        If the XIVGear API returns an unsuccessful HTTP status.
    """
    if build_url.build_provider is not BuildProvider.XIV_GEAR:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        )

    _validate_recognized_xiv_gear_link(build_url.build_url)
    response = _query_xiv_gear_sets(build_url.build_url)
    selected_index = _gearset_index(build_url.build_url, response)
    loaded_sets: list[LoadedXivGearSet] = []
    roles: set[Role] = set()

    for response_index, gear_set in enumerate(response["sets"]):
        if gear_set.get("isSeparator", False):
            continue
        role, loaded_set = _process_xiv_gear_set(gear_set, response_index)
        roles.add(role)
        loaded_sets.append(loaded_set)

    if not loaded_sets:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        )
    if len(roles) != 1:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.XIV_GEAR
        )

    return LoadedXivGearBuild(
        build_url=build_url,
        build_index=selected_index,
        build_role=roles.pop(),
        sets=loaded_sets,
    )


if __name__ == "__main__":
    raw_url = "https://xivgear.app/?page=sl%7C01a73d6f-8f17-4aa5-acc8-a8f9ad911119"  # PCT build
    raw_url = "https://xivgear.app/?page=sl%7Cf49f08b0-ce11-470f-a967-3e7613321213"  # BRD build
    raw_url = "https://xivgear.app/?page=sl%7C9ee61d69-7daa-41bd-9c28-8a0f0055f90f"  # DRK build
    raw_url = "https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b"
    raw_url = "https://xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=3"

    build_url = BuildUrl(build_url=AnyHttpUrl(raw_url))
    loaded_build = load_xiv_gear_build(build_url)
    print(loaded_build)
