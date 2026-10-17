"""Canonical stat limits for entered job statistics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StatRange:
    """Inclusive limits for a numeric job stat."""

    lower: int
    upper: int


STAT_RANGES = {
    "main_stat": StatRange(lower=3200, upper=6700),
    "determination": StatRange(lower=380, upper=5000),
    "speed_stat": StatRange(lower=380, upper=5000),
    "critical_hit": StatRange(lower=380, upper=5000),
    "direct_hit": StatRange(lower=380, upper=5000),
    "weapon_damage": StatRange(lower=50, upper=250),
    "tenacity": StatRange(lower=380, upper=5000),
}
