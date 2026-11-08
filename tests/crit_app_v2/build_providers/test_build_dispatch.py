"""Tests for provider dispatch and exception normalization."""

import pytest
import requests
from pydantic import AnyHttpUrl

from crit_app_v2.build_providers import (
    BuildErrorCategory,
    BuildProvider,
    BuildProviderError,
    BuildUrl,
)
from crit_app_v2.build_providers.build_dispatch import (
    load_job_build,
    validate_job_build_url,
)
from crit_app_v2.build_providers.etro import _process_etro_id


def _build_url(provider: BuildProvider = BuildProvider.XIV_GEAR) -> BuildUrl:
    host = "etro.gg/gearset/11111111-1111-4111-8111-111111111111"
    if provider is BuildProvider.XIV_GEAR:
        host = "xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
    return BuildUrl(build_url=AnyHttpUrl(f"https://{host}"))


def test_validate_job_build_url_normalizes_invalid_input():
    """Normalize unsupported URLs as invalid input."""
    with pytest.raises(BuildProviderError) as error:
        validate_job_build_url("https://example.com/build")

    assert error.value.category is BuildErrorCategory.INVALID_URL
    assert error.value.provider is None


def test_etro_invalid_uuid_is_normalized_as_rejected_url():
    """Reject malformed Etro gearset identifiers."""
    build_url = BuildUrl(build_url=AnyHttpUrl("https://etro.gg/gearset/3e100ab0-f774-4a21-8fd2-0958f05e28dbdd"))

    with pytest.raises(BuildProviderError) as error:
        _process_etro_id(build_url)

    assert error.value.category is BuildErrorCategory.REJECTED
    assert error.value.provider is BuildProvider.ETRO


@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (400, BuildErrorCategory.REJECTED),
        (404, BuildErrorCategory.REJECTED),
        (408, BuildErrorCategory.PROVIDER_UNAVAILABLE),
        (429, BuildErrorCategory.PROVIDER_UNAVAILABLE),
        (500, BuildErrorCategory.PROVIDER_UNAVAILABLE),
    ],
    ids=[
        "400-rejected",
        "404-rejected",
        "408-unavailable",
        "429-unavailable",
        "500-unavailable",
    ],
)
def test_http_status_is_normalized(monkeypatch, status_code, category):
    """Map HTTP status codes to provider error categories."""
    response = requests.Response()
    response.status_code = status_code

    def fail_load(_url):
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(
        "crit_app_v2.build_providers.build_dispatch._load_provider_build",
        fail_load,
    )

    with pytest.raises(BuildProviderError) as error:
        load_job_build(_build_url())

    assert error.value.category is category
    assert error.value.status_code == status_code
    assert error.value.provider is BuildProvider.XIV_GEAR


@pytest.mark.parametrize(
    ("exception", "category"),
    [
        (requests.Timeout("timeout"), BuildErrorCategory.PROVIDER_UNAVAILABLE),
        (requests.ConnectionError("network"), BuildErrorCategory.PROVIDER_UNAVAILABLE),
        (KeyError("response field"), BuildErrorCategory.UNEXPECTED_RESPONSE),
    ],
    ids=["timeout", "network-error", "unexpected-response"],
)
def test_provider_exceptions_are_normalized(monkeypatch, exception, category):
    """Map provider exceptions to stable error categories."""

    def fail_load(_url):
        raise exception

    monkeypatch.setattr(
        "crit_app_v2.build_providers.build_dispatch._load_provider_build",
        fail_load,
    )

    with pytest.raises(BuildProviderError) as error:
        load_job_build(_build_url())

    assert error.value.category is category
