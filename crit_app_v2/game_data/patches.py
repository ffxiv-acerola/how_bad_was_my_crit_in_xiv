"""Patch timing, balance-patch, and server-region reference data."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from crit_app_v2.game_data.region.server import PatchRegion, ServerRegion

_PACIFIC = ZoneInfo("America/Los_Angeles")


class Patch(StrEnum):
    """Supported Final Fantasy XIV patch identifiers."""

    P6_4 = "6.4"
    P6_5 = "6.5"
    P7_0 = "7.0"
    P7_01 = "7.01"
    P7_05 = "7.05"
    P7_1 = "7.1"
    P7_2 = "7.2"
    P7_25 = "7.25"
    P7_3 = "7.3"
    P7_4 = "7.4"
    P7_41 = "7.41"
    P7_45 = "7.45"
    P7_5 = "7.5"
    P8_0 = "8.0"

    @property
    def number(self) -> float:
        """Return the numeric patch key used by FFLogs rotation calculations."""
        return float(self.value)


PATCH_SEQUENCE = tuple(patch for patch in Patch if patch is not Patch.P8_0)


@dataclass(frozen=True)
class PatchTimes:
    """Patch start, exclusive end, and balance patch for one region."""

    patch: Patch
    balance_patch: Patch
    start_date: datetime
    end_date: datetime | None

    def __post_init__(self) -> None:
        """Require aware, ordered datetimes in the canonical Pacific timezone."""
        if self.start_date.tzinfo is None or self.start_date.utcoffset() is None:
            raise ValueError("Patch start_date must be timezone-aware.")
        if self.start_date.tzinfo != _PACIFIC:
            raise ValueError("Patch start_date must use America/Los_Angeles.")
        if self.end_date is not None:
            if self.end_date.tzinfo is None or self.end_date.utcoffset() is None:
                raise ValueError("Patch end_date must be timezone-aware.")
            if self.end_date.tzinfo != _PACIFIC:
                raise ValueError("Patch end_date must use America/Los_Angeles.")
            if self.end_date <= self.start_date:
                raise ValueError("Patch end_date must be later than start_date.")

    @property
    def start_ms(self) -> int:
        """Return the inclusive start as Unix milliseconds."""
        return int(self.start_date.timestamp() * 1000)

    @property
    def end_ms(self) -> int | None:
        """Return the exclusive end as Unix milliseconds, or None if open-ended."""
        return (
            int(self.end_date.timestamp() * 1000) if self.end_date is not None else None
        )

    def contains(self, timestamp_ms: int) -> bool:
        """Return whether a Unix-millisecond timestamp falls in this patch range."""
        end_ms = self.end_ms
        return timestamp_ms >= self.start_ms and (
            end_ms is None or timestamp_ms < end_ms
        )


@dataclass(frozen=True)
class BalancePatchRange:
    """Half-open validity range for one potency-table balance patch."""

    start: Patch
    end: Patch

    def __post_init__(self) -> None:
        """Require an increasing balance-patch interval."""
        if self.start.number >= self.end.number:
            raise ValueError("Balance patch end must be later than its start.")


class PatchLookupError(ValueError):
    """Raised when no patch range corresponds to a server and log timestamp."""


def _pacific_date(year: int, month: int, day: int) -> datetime:
    """Create midnight on a calendar date in Pacific time."""
    return datetime(year, month, day, tzinfo=_PACIFIC)


_GLOBAL_STARTS: dict[Patch, tuple[datetime, Patch]] = {
    Patch.P6_4: (_pacific_date(2023, 5, 23), Patch.P6_4),
    Patch.P6_5: (_pacific_date(2023, 10, 3), Patch.P6_5),
    # 7.0 early access is when logs begin using 7.0 combat data.
    Patch.P7_0: (_pacific_date(2024, 6, 28), Patch.P7_0),
    Patch.P7_01: (_pacific_date(2024, 7, 16), Patch.P7_01),
    Patch.P7_05: (_pacific_date(2024, 7, 30), Patch.P7_05),
    Patch.P7_1: (_pacific_date(2024, 11, 12), Patch.P7_1),
    Patch.P7_2: (_pacific_date(2025, 3, 25), Patch.P7_2),
    Patch.P7_25: (_pacific_date(2025, 5, 27), Patch.P7_25),
    Patch.P7_3: (_pacific_date(2025, 8, 5), Patch.P7_3),
    Patch.P7_4: (_pacific_date(2025, 12, 16), Patch.P7_4),
    Patch.P7_41: (_pacific_date(2026, 1, 27), Patch.P7_41),
    Patch.P7_45: (_pacific_date(2026, 3, 3), Patch.P7_45),
    Patch.P7_5: (_pacific_date(2026, 4, 28), Patch.P7_5),
}

_CN_STARTS: dict[Patch, tuple[datetime, Patch]] = {
    Patch.P6_4: (_pacific_date(2023, 9, 19), Patch.P6_4),
    Patch.P6_5: (_pacific_date(2024, 3, 5), Patch.P6_5),
    Patch.P7_0: (_pacific_date(2024, 9, 27), Patch.P7_05),
    Patch.P7_01: (_pacific_date(2024, 10, 22), Patch.P7_05),
    Patch.P7_05: (_pacific_date(2024, 11, 12), Patch.P7_05),
    Patch.P7_1: (_pacific_date(2025, 2, 18), Patch.P7_1),
    Patch.P7_2: (_pacific_date(2025, 6, 24), Patch.P7_25),
    Patch.P7_3: (_pacific_date(2025, 9, 16), Patch.P7_3),
}

_KO_STARTS: dict[Patch, tuple[datetime, Patch]] = {
    Patch.P6_4: (_pacific_date(2023, 10, 31), Patch.P6_4),
    Patch.P6_5: (_pacific_date(2024, 4, 2), Patch.P6_5),
    Patch.P7_0: (_pacific_date(2024, 12, 3), Patch.P7_05),
    Patch.P7_01: (_pacific_date(2024, 12, 24), Patch.P7_05),
    Patch.P7_05: (_pacific_date(2025, 1, 14), Patch.P7_05),
    Patch.P7_1: (_pacific_date(2025, 3, 18), Patch.P7_1),
    Patch.P7_2: (_pacific_date(2025, 7, 15), Patch.P7_25),
    Patch.P7_3: (_pacific_date(2025, 10, 28), Patch.P7_3),
    Patch.P7_4: (_pacific_date(2026, 2, 3), Patch.P7_45),
}

PATCH_CATCH_UP: dict[PatchRegion, Patch] = {
    PatchRegion.CN: Patch.P7_4,
    PatchRegion.KO: Patch.P7_5,
}


def _build_patch_times(
    starts: Mapping[Patch, tuple[datetime, Patch]],
) -> dict[Patch, PatchTimes]:
    """Build contiguous half-open timing records from ordered patch starts."""
    ordered_starts = sorted(starts.items(), key=lambda item: item[1][0])
    result: dict[Patch, PatchTimes] = {}
    for index, (patch, (start_date, balance_patch)) in enumerate(ordered_starts):
        end_date = (
            ordered_starts[index + 1][1][0] if index + 1 < len(ordered_starts) else None
        )
        result[patch] = PatchTimes(
            patch=patch,
            balance_patch=balance_patch,
            start_date=start_date,
            end_date=end_date,
        )
    return result


def _regional_starts(
    overrides: Mapping[Patch, tuple[datetime, Patch]], catch_up_patch: Patch
) -> dict[Patch, tuple[datetime, Patch]]:
    """Append global patch starts from the region's synchronization point."""
    starts = {
        patch: start
        for patch, start in overrides.items()
        if patch.number < catch_up_patch.number
    }
    starts.update(
        {
            patch: start
            for patch, start in _GLOBAL_STARTS.items()
            if patch.number >= catch_up_patch.number
        }
    )
    return starts


patch_times_global = _build_patch_times(_GLOBAL_STARTS)
patch_times_cn = _build_patch_times(
    _regional_starts(_CN_STARTS, PATCH_CATCH_UP[PatchRegion.CN])
)
patch_times_ko = _build_patch_times(
    _regional_starts(_KO_STARTS, PATCH_CATCH_UP[PatchRegion.KO])
)

PATCH_TIMES_BY_REGION: dict[PatchRegion, dict[Patch, PatchTimes]] = {
    PatchRegion.GLOBAL: patch_times_global,
    PatchRegion.CN: patch_times_cn,
    PatchRegion.KO: patch_times_ko,
}


def _build_balance_patch_ranges() -> dict[Patch, BalancePatchRange]:
    """Derive potency validity intervals from the ordered patch identifiers."""
    patches = PATCH_SEQUENCE
    return {
        patch: BalancePatchRange(
            start=patch,
            end=patches[index + 1] if index + 1 < len(patches) else Patch.P8_0,
        )
        for index, patch in enumerate(patches)
    }


BALANCE_PATCH_RANGES = _build_balance_patch_ranges()


def get_patch_times(timestamp_ms: int, server_region: ServerRegion | str) -> PatchTimes:
    """Find the patch record for a log time and its FFLogs server region.

    Parameters
    ----------
    timestamp_ms
        Log timestamp in Unix milliseconds.
    server_region
        FFLogs compact region name or corresponding ``ServerRegion``.

    Returns
    -------
    PatchTimes
        Timing and potency-balance metadata for the matching patch.

    Raises
    ------
    PatchLookupError
        If the region is unknown or its patch table does not cover the timestamp.
    """
    try:
        region = ServerRegion(server_region)
    except ValueError as error:
        raise PatchLookupError(f"Unknown FFLogs region: {server_region!r}.") from error

    patch_region = region.patch_region
    for patch_times in PATCH_TIMES_BY_REGION[patch_region].values():
        if patch_times.contains(timestamp_ms):
            return patch_times
    raise PatchLookupError(
        f"No patch timing for {region.value} at Unix timestamp {timestamp_ms}."
    )
