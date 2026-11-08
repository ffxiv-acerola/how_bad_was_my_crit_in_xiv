"""Fetch Etro gearsets and normalize their validated response data."""

import re
from urllib.parse import urlsplit
from uuid import UUID

import coreapi
from pydantic import UUID4, TypeAdapter
from pydantic.networks import AnyHttpUrl

from crit_app_v2.build_providers.errors import BuildErrorCategory, BuildProviderError
from crit_app_v2.build_providers.models import (
    BuildProvider,
    BuildUrl,
    EtroBuildResponse,
    LoadedEtroBuild,
    RoleBuildStatsModel,
)
from crit_app_v2.game_data.jobs import JOB_SPECS
from crit_app_v2.game_data.roles import ROLE_SPECS
from crit_app_v2.game_data.stats import MAIN_STAT_SPEC, SPEED_STAT_SPEC

uuid4_adapter = TypeAdapter(UUID4)


def _list_gearset(gearset_id: UUID4) -> EtroBuildResponse:
    """Fetch an Etro gearset using its ID.

    Parameters
    ----------
    gearset_id
        UUID4 identifying the Etro gearset to fetch.

    Returns
    -------
    EtroBuildResponse
        Validated response fields consumed by the Etro build loader.

    Raises
    ------
    coreapi.exceptions.CoreAPIException
        If the CoreAPI client cannot retrieve or perform the gearset request.
    pydantic.ValidationError
        If the response lacks valid fields required by the loader.
    """
    # Initialize a client & load the schema document
    gearset_action = ["gearsets", "read"]
    gearset_params = {
        "id": str(gearset_id),
    }
    client = coreapi.Client()
    schema = client.get("https://etro.gg/api/docs/")
    build_result = client.action(schema, gearset_action, params=gearset_params)
    return EtroBuildResponse.model_validate(build_result)


def _process_etro_id(build_url: BuildUrl) -> UUID:
    """Extract and validate the gearset UUID from an Etro URL.

    Parameters
    ----------
    build_url
        Validated build URL classified as an Etro URL.

    Returns
    -------
    UUID
        UUID4 identifying the Etro gearset.

    Raises
    ------
    BuildProviderError
        If the URL is not a valid Etro gearset link or contains an invalid UUID.
    """
    if build_url.build_provider != BuildProvider.ETRO:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.ETRO
        )

    path = urlsplit(str(build_url.build_url)).path
    match = re.fullmatch(r"/gearset/([^/]+)/?", path)

    if match is None:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.ETRO
        )

    try:
        return uuid4_adapter.validate_python(match.group(1))
    except ValueError as error:
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=BuildProvider.ETRO
        ) from error


def _process_etro_name(etro_build_response: EtroBuildResponse) -> str:
    """Get the build name from an Etro API response.

    Parameters
    ----------
    etro_build_response
        Validated response from the Etro gearset API.

    Returns
    -------
    str
        Name assigned to the gearset.
    """
    return etro_build_response.name


def _process_etro_stats(
    etro_build_response: EtroBuildResponse,
) -> RoleBuildStatsModel:
    """Convert Etro's job parameters into role build stats.

    The job selects the main-stat field from the response, while the role
    determines the applicable speed stat and whether Tenacity is included.

    Parameters
    ----------
    etro_build_response
        Validated Etro response. Its job determines the main stat and role-
        specific speed and Tenacity requirements.

    Returns
    -------
    RoleBuildStatsModel
        Normalized stats, with the party bonus removed from the main stat.
    """
    job = etro_build_response.job
    role = JOB_SPECS[job].role
    main_stat_name = MAIN_STAT_SPEC[JOB_SPECS[job].main_stat].etro_name
    requires_tenacity = ROLE_SPECS[role].requires_tenacity
    total_params = etro_build_response.required_stats

    main_stat = int(total_params[main_stat_name] / etro_build_response.party_bonus) + 1

    if requires_tenacity:
        tenacity = total_params["TEN"]
    else:
        tenacity = None

    return RoleBuildStatsModel(
        main_stat=main_stat,
        determination=total_params["DET"],
        speed_stat=total_params[SPEED_STAT_SPEC[ROLE_SPECS[role].speed_stat].etro_name],
        critical_hit=total_params["CRT"],
        direct_hit=total_params["DH"],
        weapon_damage=total_params["Weapon Damage"],
        tenacity=tenacity,
    )


def load_etro_build(build_url: BuildUrl):
    """Load and normalize an Etro build from its validated URL.

    Extracts the gearset ID, fetches the API response, and builds the
    normalized role, name, and stats model.

    Parameters
    ----------
    build_url
        Validated build URL classified as an Etro URL.

    Returns
    -------
    LoadedEtroBuild
        Normalized Etro build data containing the source URL, ID, name, role,
        and role-level stats.

    Raises
    ------
    BuildProviderError
        If the URL is not a valid Etro gearset URL. API and response-validation
        errors propagate for normalization by the provider dispatcher.
    """
    build_id = _process_etro_id(build_url)
    response = _list_gearset(build_id)

    build_name = _process_etro_name(response)
    job = response.job
    role = JOB_SPECS[job].role
    build_stats = _process_etro_stats(response)

    return LoadedEtroBuild(
        build_url=build_url,
        build_id=build_id,
        build_name=build_name,
        build_role=role,
        build_stats=build_stats,
    )


if __name__ == "__main__":
    etro_link = "https://etro.gg/gearset/1dde8dd8-0953-4760-a5a4-1710a023f064"
    build_url = BuildUrl(build_url=AnyHttpUrl(etro_link))
    etro_build_model = load_etro_build(build_url)

    print(etro_build_model)
