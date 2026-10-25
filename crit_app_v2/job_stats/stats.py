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
        """Format the inclusive stat range for an input placeholder.

        Returns
        -------
        str
            The range formatted as ``lower - upper``.
        """
        return f"{self.lower} - {self.upper}"

    def stat_label(self, role: Role) -> str:
        """Return the label for this stat and role.

        Parameters
        ----------
        role
            Role used to resolve role-specific stat labels.

        Returns
        -------
        str
            The display label for the statistic.
        """
        if self.stat_name == Stats.MAIN_STAT:
            return ROLE_SPECS[role].main_stat_label
        elif self.stat_name == Stats.SPEED_STAT:
            return ROLE_SPECS[role].speed_stat_label
        else:
            return self.stat_name.replace("_", " ").capitalize()


_INPUTS = [
    StatInput(Stats.MAIN_STAT, 3200, 6700),
    StatInput(Stats.DETERMINATION, 380, 5000),
    StatInput(Stats.SPEED_STAT, 380, 5000),
    StatInput(Stats.CRITICAL_HIT, 380, 5000),
    StatInput(Stats.DIRECT_HIT, 380, 5000),
    StatInput(Stats.WEAPON_DAMAGE, 50, 250),
    StatInput(Stats.TENACITY, 380, 5000),
]
STAT_INPUTS = {s.stat_name: s for s in _INPUTS}
