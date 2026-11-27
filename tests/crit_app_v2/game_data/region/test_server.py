"""Tests for region enums and the current world-region mapping."""

import pytest

from crit_app_v2.game_data import PatchRegion, Region, ServerRegion, world_to_region
from crit_app_v2.game_data.region.server import WORLD_REGIONS


@pytest.mark.parametrize(
    "server_region,patch_region",
    [
        (ServerRegion.NORTH_AMERICA, PatchRegion.GLOBAL),
        (ServerRegion.EUROPE, PatchRegion.GLOBAL),
        (ServerRegion.JAPAN, PatchRegion.GLOBAL),
        (ServerRegion.OCEANIA, PatchRegion.GLOBAL),
        (ServerRegion.KOREA, PatchRegion.KO),
        (ServerRegion.CHINA, PatchRegion.CN),
    ],
    ids=["na-global", "eu-global", "jp-global", "oc-global", "kr-korea", "cn-china"],
)
def test_server_region_resolves_to_patch_cadence(server_region: ServerRegion, patch_region: PatchRegion) -> None:
    """Map every FFLogs server region to its patch cadence."""
    assert server_region.patch_region is patch_region


def test_japan_compact_name_matches_fflogs_response() -> None:
    """Use FFLogs's ``JP`` compact region name for Japan."""
    assert ServerRegion.JAPAN.value == "JP"
    assert ServerRegion.JAPAN.analytics_region is Region.JAPAN


def test_world_mapping_values_are_formal_analytics_regions() -> None:
    """Map every configured player world to a Region enum value."""
    assert WORLD_REGIONS
    assert all(isinstance(region, Region) for region in WORLD_REGIONS.values())


def test_world_to_region_returns_world_region() -> None:
    """Resolve a configured world name to its analytics region."""
    assert world_to_region("Adamantoise") is Region.NORTH_AMERICA


def test_world_to_region_rejects_unknown_world() -> None:
    """Reject world names absent from the static mapping."""
    with pytest.raises(ValueError, match="Unknown FFLogs player world"):
        world_to_region("Unknown World")
