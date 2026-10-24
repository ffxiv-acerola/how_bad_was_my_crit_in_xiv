"""Framework-independent role metadata for job-stat consumers."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Supported combat roles for entered job statistics."""

    TANK = "Tank"
    HEALER = "Healer"
    MELEE = "Melee"
    PHYSICAL_RANGED = "Physical Ranged"
    MAGICAL_RANGED = "Magical Ranged"


@dataclass(frozen=True)
class RoleSpec:
    """Labels and behavior that follow directly from a combat role."""

    main_stat_label: str
    speed_stat_label: str
    requires_tenacity: bool


ROLE_SPECS = {
    Role.TANK: RoleSpec(
        main_stat_label="Strength",
        speed_stat_label="Skill speed",
        requires_tenacity=True,
    ),
    Role.HEALER: RoleSpec(
        main_stat_label="Mind",
        speed_stat_label="Spell speed",
        requires_tenacity=False,
    ),
    Role.MELEE: RoleSpec(
        main_stat_label="Srength/Dexterity",
        speed_stat_label="Skill speed",
        requires_tenacity=False,
    ),
    Role.PHYSICAL_RANGED: RoleSpec(
        main_stat_label="Dexterity",
        speed_stat_label="Skill speed",
        requires_tenacity=False,
    ),
    Role.MAGICAL_RANGED: RoleSpec(
        main_stat_label="Intelligence",
        speed_stat_label="Spell speed",
        requires_tenacity=False,
    ),
}
