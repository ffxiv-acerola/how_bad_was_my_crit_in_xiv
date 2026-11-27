"""Tests for patch dates, balance mappings, and server regions."""

from datetime import datetime

import pytest

from crit_app_v2.game_data import (
    BALANCE_PATCH_RANGES,
    PATCH_CATCH_UP,
    PATCH_SEQUENCE,
    PATCH_TIMES_BY_REGION,
    Patch,
    PatchLookupError,
    PatchRegion,
    PatchTimes,
    ServerRegion,
    get_patch_times,
)


@pytest.mark.parametrize(
    "patch_region",
    [PatchRegion.GLOBAL, PatchRegion.CN, PatchRegion.KO],
    ids=["global", "china", "korea"],
)
def test_patch_ranges_are_contiguous_and_ordered(patch_region: PatchRegion) -> None:
    """Every patch row is ordered, valid, and adjacent to its successor."""
    patch_table = PATCH_TIMES_BY_REGION[patch_region]
    patch_records = list(patch_table.values())

    assert [record.patch for record in patch_records] == sorted(patch_table, key=lambda patch: patch.number)
    assert patch_records[-1].end_date is None
    for current, following in zip(patch_records, patch_records[1:], strict=False):
        assert current.end_date == following.start_date
        assert current.end_ms == following.start_ms
        assert current.start_date < current.end_date


@pytest.mark.parametrize(
    "patch_region,first_synced_patch",
    [
        (PatchRegion.CN, Patch.P7_4),
        (PatchRegion.KO, Patch.P7_5),
    ],
    ids=["china-syncs-at-7.4", "korea-syncs-at-7.5"],
)
def test_region_uses_global_rows_after_catch_up(patch_region: PatchRegion, first_synced_patch: Patch) -> None:
    """Use global patch records from each region's synchronization point."""
    regional = PATCH_TIMES_BY_REGION[patch_region]
    global_table = PATCH_TIMES_BY_REGION[PatchRegion.GLOBAL]

    assert PATCH_CATCH_UP[patch_region] is first_synced_patch
    for patch in PATCH_SEQUENCE:
        if patch.number >= first_synced_patch.number:
            assert regional[patch] == global_table[patch]


@pytest.mark.parametrize(
    "patch_region,patch,year,month,day,balance_patch",
    [
        (PatchRegion.CN, Patch.P7_05, 2024, 11, 12, Patch.P7_05),
        (PatchRegion.CN, Patch.P7_1, 2025, 2, 18, Patch.P7_1),
        (PatchRegion.CN, Patch.P7_2, 2025, 6, 24, Patch.P7_25),
        (PatchRegion.KO, Patch.P7_05, 2025, 1, 14, Patch.P7_05),
        (PatchRegion.KO, Patch.P7_2, 2025, 7, 15, Patch.P7_25),
        (PatchRegion.KO, Patch.P7_3, 2025, 10, 28, Patch.P7_3),
        (PatchRegion.KO, Patch.P7_4, 2026, 2, 3, Patch.P7_45),
    ],
    ids=[
        "cn-7.05",
        "cn-7.1",
        "cn-7.2-rolls-7.25",
        "ko-7.05",
        "ko-7.2-rolls-7.25",
        "ko-7.3",
        "ko-7.4-rolls-7.45",
    ],
)
def test_regional_patch_dates_and_balance_mapping(
    patch_region: PatchRegion,
    patch: Patch,
    year: int,
    month: int,
    day: int,
    balance_patch: Patch,
) -> None:
    """Keep cited CN and KO rollout dates and balance rolls represented."""
    record = PATCH_TIMES_BY_REGION[patch_region][patch]

    assert (record.start_date.year, record.start_date.month, record.start_date.day) == (
        year,
        month,
        day,
    )
    assert record.balance_patch is balance_patch


def test_patch_time_lookup_includes_start_and_excludes_end() -> None:
    """Resolve inclusive starts and exclusive ends for a regional patch range."""
    record = PATCH_TIMES_BY_REGION[PatchRegion.KO][Patch.P7_3]
    assert get_patch_times(record.start_ms, ServerRegion.KOREA) == record
    assert get_patch_times(record.end_ms or 0, ServerRegion.KOREA) != record


@pytest.mark.parametrize(
    "timestamp_ms,server_region",
    [
        (0, ServerRegion.NORTH_AMERICA),
        (0, "unknown"),
    ],
    ids=["before-known-patches", "unknown-region"],
)
def test_patch_time_lookup_rejects_unknown_ranges(timestamp_ms: int, server_region: ServerRegion | str) -> None:
    """Raise a typed lookup error rather than returning an invalid patch number."""
    with pytest.raises(PatchLookupError):
        get_patch_times(timestamp_ms, server_region)


def test_balance_patch_ranges_cover_csv_patch_sequence() -> None:
    """Derive contiguous balance ranges for all potency data patch versions."""
    assert tuple(BALANCE_PATCH_RANGES) == PATCH_SEQUENCE
    for index, patch in enumerate(PATCH_SEQUENCE):
        expected_end = PATCH_SEQUENCE[index + 1] if index + 1 < len(PATCH_SEQUENCE) else Patch.P8_0
        patch_range = BALANCE_PATCH_RANGES[patch]
        assert patch_range.start is patch
        assert patch_range.end is expected_end


def test_balance_patch_ranges_cover_all_potency_source_files() -> None:
    """Map every source potency CSV filename to a configured balance range."""
    from pathlib import Path

    source_directory = Path(__file__).resolve().parents[3] / "fflogs_rotation" / "job_data" / "potencies"
    source_patches = {Patch(path.stem.split("-")[0].replace("_", ".")) for path in source_directory.glob("**/*.csv")}

    assert source_patches
    assert source_patches == set(BALANCE_PATCH_RANGES)


def test_patch_times_reject_naive_datetimes() -> None:
    """Require aware timestamps when constructing patch timing records."""
    with pytest.raises(ValueError, match="timezone-aware"):
        PatchTimes(
            patch=Patch.P7_0,
            balance_patch=Patch.P7_0,
            start_date=datetime(2024, 6, 28),
            end_date=None,
        )
