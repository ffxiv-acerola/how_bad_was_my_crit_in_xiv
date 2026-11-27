"""Tests for the FFLogs rotation patch-time adapter."""

import subprocess
import sys

import pytest

from crit_app_v2.game_data import (
    PATCH_TIMES_BY_REGION,
    PatchLookupError,
    PatchRegion,
    ServerRegion,
)
from fflogs_rotation.actions import ActionTable


@pytest.mark.parametrize(
    "patch_region,server_region",
    [
        (PatchRegion.GLOBAL, ServerRegion.NORTH_AMERICA),
        (PatchRegion.GLOBAL, ServerRegion.EUROPE),
        (PatchRegion.GLOBAL, ServerRegion.JAPAN),
        (PatchRegion.GLOBAL, ServerRegion.OCEANIA),
        (PatchRegion.KO, ServerRegion.KOREA),
        (PatchRegion.CN, ServerRegion.CHINA),
    ],
    ids=["na-global", "eu-global", "jp-global", "oc-global", "ko", "cn"],
)
def test_action_table_maps_each_patch_range_to_balance_patch(
    patch_region: PatchRegion, server_region: ServerRegion
) -> None:
    """Resolve each patch start and final included millisecond correctly."""
    for record in PATCH_TIMES_BY_REGION[patch_region].values():
        assert ActionTable._get_patch_number(record.start_ms, server_region.value) == record.balance_patch.number
        if record.end_ms is not None:
            assert ActionTable._get_patch_number(record.end_ms - 1, server_region.value) == record.balance_patch.number


def test_action_table_patch_lookup_rejects_unknown_region() -> None:
    """Raise a patch lookup error instead of returning the old 0.0 sentinel."""
    with pytest.raises(PatchLookupError, match="Unknown FFLogs region"):
        ActionTable._get_patch_number(1_750_000_000_000, "unknown")


def test_action_table_patch_lookup_rejects_uncovered_timestamp() -> None:
    """Raise when a fight timestamp is outside every patch range."""
    with pytest.raises(PatchLookupError, match="No patch timing"):
        ActionTable._get_patch_number(0, ServerRegion.NORTH_AMERICA.value)


def test_importing_action_table_does_not_load_legacy_dash_components() -> None:
    """Keep the shared rotation engine free of legacy UI component imports."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """import sys
import fflogs_rotation.actions
assert "crit_app.job_data.roles" not in sys.modules
assert "dash_bootstrap_components" not in sys.modules
""",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
