"""Canonical stat limits for entered job statistics."""

from dataclasses import dataclass
from enum import StrEnum

from crit_app_v2.job_stats.roles import ROLE_SPECS, Role


class Stats(StrEnum):
    MAIN_STAT = "main_stat"
    DETERMINATION = "determination"
    SPEED_STAT = "speed_stat"
    CRITICAL_HIT = "critical_hit"
    DIRECT_HIT = "direct_hit"
    WEAPON_DAMAGE = "weapon_damage"
    TENACITY = "tenacity"


@dataclass(frozen=True)
class StatInput:
    """Inclusive limits for a numeric job stat."""

    stat_name: Stats
    lower: int
    upper: int

    def placeholder_text(self) -> str:
        """Formatted placeholder text in dmc.NumberInput."""
        return f"{self.lower} - {self.upper}"

    def stat_label(self, role: Role) -> str:
        """Resolve stat/role-specific label."""
        if self.stat_name == Stats.MAIN_STAT:
            return ROLE_SPECS[role].main_stat_label
        elif self.stat_name == Stats.SPEED_STAT:
            return ROLE_SPECS[role].speed_stat_label
        else:
            return self.stat_name.replace("_", " ").capitalize()


STAT_INPUTS = {
    Stats.MAIN_STAT: StatInput(stat_name=Stats.MAIN_STAT, lower=3200, upper=6700),
    Stats.DETERMINATION: StatInput(
        stat_name=Stats.DETERMINATION, lower=380, upper=5000
    ),
    Stats.SPEED_STAT: StatInput(stat_name=Stats.SPEED_STAT, lower=380, upper=5000),
    Stats.CRITICAL_HIT: StatInput(stat_name=Stats.CRITICAL_HIT, lower=380, upper=5000),
    Stats.DIRECT_HIT: StatInput(stat_name=Stats.DIRECT_HIT, lower=380, upper=5000),
    Stats.WEAPON_DAMAGE: StatInput(stat_name=Stats.WEAPON_DAMAGE, lower=50, upper=250),
    Stats.TENACITY: StatInput(stat_name=Stats.TENACITY, lower=380, upper=5000),
}
