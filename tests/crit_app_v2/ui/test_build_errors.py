"""Tests for rendering normalized build-provider errors."""

import pytest

from crit_app_v2.build_providers import (
    BuildErrorCategory,
    BuildProvider,
    BuildProviderError,
)
from crit_app_v2.ui.build_errors import build_error_message


def test_invalid_url_message_is_provider_independent():
    """Show a provider-neutral message for invalid URLs."""
    error = BuildProviderError(BuildErrorCategory.INVALID_URL)

    assert build_error_message(error) == ("Invalid or unsupported URL. Enter a valid Etro or XIVGear build URL.")


@pytest.mark.parametrize(
    ("provider", "expected_prefix"),
    [
        (BuildProvider.ETRO, "Etro rejected this URL or build."),
        (BuildProvider.XIV_GEAR, "XIVGear rejected this URL or build."),
    ],
    ids=["etro", "xivgear"],
)
def test_rejected_build_message_names_provider(provider, expected_prefix):
    """Name the provider that rejected a build."""
    error = BuildProviderError(BuildErrorCategory.REJECTED, provider=provider)

    assert build_error_message(error).startswith(expected_prefix)


def test_unavailable_provider_without_details_uses_retry_message():
    """Show a retry message when provider details are absent."""
    error = BuildProviderError(BuildErrorCategory.PROVIDER_UNAVAILABLE, provider=BuildProvider.ETRO)

    assert build_error_message(error) == "Could not reach Etro. Please try again later."


@pytest.mark.parametrize("status_code", [408, 429], ids=["timeout", "rate-limited"])
def test_xivgear_timeout_or_rate_limit_has_retry_message(status_code):
    """Show a retry message for temporary XIVGear failures."""
    error = BuildProviderError(
        BuildErrorCategory.PROVIDER_UNAVAILABLE,
        provider=BuildProvider.XIV_GEAR,
        status_code=status_code,
    )

    assert build_error_message(error) == ("XIVGear is temporarily unavailable. Please try again later.")


@pytest.mark.parametrize("status_code", [500, 503], ids=["server-error", "unavailable"])
def test_xivgear_server_error_advises_checking_link_or_retrying(status_code):
    """Advise checking the link after XIVGear server failures."""
    error = BuildProviderError(
        BuildErrorCategory.PROVIDER_UNAVAILABLE,
        provider=BuildProvider.XIV_GEAR,
        status_code=status_code,
    )

    assert build_error_message(error) == ("XIVGear couldn't load this build. Check the link or try again later.")


def test_unexpected_response_message_does_not_expose_provider_details():
    """Hide internal details from unexpected-response messages."""
    error = BuildProviderError(
        BuildErrorCategory.UNEXPECTED_RESPONSE,
        provider=BuildProvider.XIV_GEAR,
    )

    assert build_error_message(error) == ("XIVGear returned an unexpected response. Please try again later.")
