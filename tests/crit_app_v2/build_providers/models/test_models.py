"""Tests for shared build-provider URL and build models."""

import pytest
from pydantic import ValidationError

from crit_app_v2.build_providers.models import BuildProvider, BuildUrl


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://etro.gg/gearset/example", BuildProvider.ETRO),
        ("https://www.etro.gg/gearset/example", BuildProvider.ETRO),
        ("https://xivgear.app/", BuildProvider.XIV_GEAR),
        ("https://www.xivgear.app/", BuildProvider.XIV_GEAR),
        ("https://share.xivgear.app/share/example", BuildProvider.XIV_GEAR),
    ],
    ids=["etro", "www-etro", "xivgear", "www-xivgear", "xivgear-share"],
)
def test_build_url_derives_provider_from_supported_host(url, provider):
    """Classify supported provider hosts when constructing a build URL."""
    build_url = BuildUrl(build_url=url)

    assert build_url.build_provider is provider


def test_build_url_rejects_unsupported_host_at_construction():
    """Reject unsupported hosts while validating the build URL model."""
    with pytest.raises(ValidationError, match="Only etro.gg or xivgear.app"):
        BuildUrl(build_url="https://example.com/build")


def test_build_url_rejects_provider_as_extra_input():
    """Prevent callers from supplying a provider that conflicts with the URL."""
    with pytest.raises(ValidationError, match="build_provider"):
        BuildUrl(
            build_url="https://etro.gg/gearset/example",
            build_provider=BuildProvider.XIV_GEAR,
        )


def test_build_url_serialization_round_trip_derives_provider_again():
    """Serialize only the source URL and re-derive its provider on loading."""
    build_url = BuildUrl(build_url="https://etro.gg/gearset/example")

    serialized = build_url.model_dump(mode="json")

    assert serialized == {"build_url": "https://etro.gg/gearset/example"}
    restored = BuildUrl.model_validate(serialized)
    assert restored.build_provider is BuildProvider.ETRO
