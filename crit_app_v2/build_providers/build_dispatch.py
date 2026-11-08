"""Validate provider URLs, dispatch build loading, and normalize failures."""

import logging

import coreapi.exceptions
import requests
from pydantic import AnyHttpUrl, ValidationError

from crit_app_v2.build_providers import (
    BuildErrorCategory,
    BuildProvider,
    BuildProviderError,
    BuildUrl,
    LoadedEtroBuild,
    LoadedXivGearBuild,
)
from crit_app_v2.build_providers.etro import load_etro_build
from crit_app_v2.build_providers.xivgear import load_xiv_gear_build

logger = logging.getLogger(__name__)


def validate_job_build_url(raw_url: str) -> BuildUrl:
    """Validate a user-provided build URL and classify its provider.

    Parameters
    ----------
    raw_url : str
        Unparsed Etro or XIVGear URL entered by the user.

    Returns
    -------
    BuildUrl
        Validated URL with its supported provider identified.

    Raises
    ------
    BuildProviderError
        If the input is malformed or its host is not a supported provider.
    """
    try:
        return BuildUrl(build_url=AnyHttpUrl(raw_url))
    except (ValidationError, ValueError) as error:
        raise BuildProviderError(BuildErrorCategory.INVALID_URL) from error


def _load_provider_build(
    job_build_url: BuildUrl,
) -> LoadedEtroBuild | LoadedXivGearBuild:
    """Load a build using the provider classified in its URL.

    Parameters
    ----------
    job_build_url : BuildUrl
        Validated URL identifying an Etro or XIVGear build.

    Returns
    -------
    LoadedEtroBuild or LoadedXivGearBuild
        Normalized, provider-specific build data.

    Raises
    ------
    BuildProviderError
        If the provider is not supported by this dispatcher.
    Exception
        Provider-specific loading errors, which are normalized by
        :func:`load_job_build`.
    """
    if job_build_url.build_provider == BuildProvider.ETRO:
        return load_etro_build(job_build_url)
    if job_build_url.build_provider == BuildProvider.XIV_GEAR:
        return load_xiv_gear_build(job_build_url)
    raise BuildProviderError(
        BuildErrorCategory.REJECTED, provider=job_build_url.build_provider
    )


def load_job_build(
    job_build_url: BuildUrl,
) -> LoadedEtroBuild | LoadedXivGearBuild:
    """Load and normalize an Etro or XIVGear build.

    Provider-specific failures are converted to :class:`BuildProviderError`
    categories so callers do not need to depend on HTTP, CoreAPI, or Pydantic
    exception details.

    Parameters
    ----------
    job_build_url : BuildUrl
        Validated URL classified as a supported external build provider.

    Returns
    -------
    LoadedEtroBuild or LoadedXivGearBuild
        Normalized role-level build data from the selected provider.

    Raises
    ------
    BuildProviderError
        If the provider rejects the URL or build, is unavailable, returns an
        unexpected response, or the URL cannot be used by a supported provider.
    """
    provider = job_build_url.build_provider
    try:
        return _load_provider_build(job_build_url)
    except BuildProviderError:
        # Keep errors that already have a clear category unchanged.
        raise
    except requests.exceptions.JSONDecodeError as error:
        # The provider responded, but its body was not valid JSON.
        raise BuildProviderError(
            BuildErrorCategory.UNEXPECTED_RESPONSE, provider=provider
        ) from error
    except requests.HTTPError as error:
        # Treat rejected requests separately from temporary or server failures.
        response = error.response
        status_code = response.status_code if response is not None else None
        if status_code in (408, 429) or status_code is None or status_code >= 500:
            category = BuildErrorCategory.PROVIDER_UNAVAILABLE
        else:
            category = BuildErrorCategory.REJECTED
        raise BuildProviderError(
            category, provider=provider, status_code=status_code
        ) from error
    except (requests.RequestException, coreapi.exceptions.NetworkError) as error:
        # The request could not complete because of a connection-level problem.
        raise BuildProviderError(
            BuildErrorCategory.PROVIDER_UNAVAILABLE, provider=provider
        ) from error
    except (
        coreapi.exceptions.ErrorMessage,
        coreapi.exceptions.LinkLookupError,
        coreapi.exceptions.ParameterError,
    ) as error:
        # The provider could not find or accept the requested build operation.
        raise BuildProviderError(
            BuildErrorCategory.REJECTED, provider=provider
        ) from error
    except ValidationError as error:
        # A bad Etro UUID means a rejected link; other invalid data is a bad response.
        if any(detail.get("type", "").startswith("uuid_") for detail in error.errors()):
            category = BuildErrorCategory.REJECTED
        else:
            category = BuildErrorCategory.UNEXPECTED_RESPONSE
        raise BuildProviderError(category, provider=provider) from error
    except Exception as error:
        # Log unforeseen failures, then expose only a safe generic category.
        logger.exception("Unexpected error while loading a %s build", provider.value)
        raise BuildProviderError(
            BuildErrorCategory.UNEXPECTED_RESPONSE, provider=provider
        ) from error
