"""Framework-independent role metadata for job-stat consumers."""

from dataclasses import dataclass
from enum import StrEnum

from crit_app_v2.game_data.stats import SpeedStats


class Role(StrEnum):
    """Supported combat roles for entered job statistics."""

    TANK = "Tank"
    HEALER = "Healer"
    MELEE = "Melee"
    PHYSICAL_RANGED = "Physical Ranged"
    MAGICAL_RANGED = "Magical Ranged"


@dataclass(frozen=True)
class RoleSpec:
    """Labels and stat requirements associated with one combat role.

    Parameters
    ----------
    role
        Role represented by this specification.
    main_stat_label
        UI label for the role's main stat.
    speed_stat
        Domain key for the role's speed stat.
    requires_tenacity
        Whether builds for the role require Tenacity.
    """

    role: Role
    main_stat_label: str
    speed_stat: SpeedStats
    requires_tenacity: bool


ROLE_SPECS = {
    Role.TANK: RoleSpec(
        role=Role.TANK,
        main_stat_label="Strength",
        speed_stat=SpeedStats.SKILL_SPEED,
        requires_tenacity=True,
    ),
    Role.HEALER: RoleSpec(
        role=Role.HEALER,
        main_stat_label="Mind",
        speed_stat=SpeedStats.SPELL_SPEED,
        requires_tenacity=False,
    ),
    Role.MELEE: RoleSpec(
        role=Role.MELEE,
        main_stat_label="Strength/Dexterity",
        speed_stat=SpeedStats.SKILL_SPEED,
        requires_tenacity=False,
    ),
    Role.PHYSICAL_RANGED: RoleSpec(
        role=Role.PHYSICAL_RANGED,
        main_stat_label="Dexterity",
        speed_stat=SpeedStats.SKILL_SPEED,
        requires_tenacity=False,
    ),
    Role.MAGICAL_RANGED: RoleSpec(
        role=Role.MAGICAL_RANGED,
        main_stat_label="Intelligence",
        speed_stat=SpeedStats.SPELL_SPEED,
        requires_tenacity=False,
    ),
}
