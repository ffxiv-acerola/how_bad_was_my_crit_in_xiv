"""Framework-independent role metadata for job-stat consumers."""

from dataclasses import dataclass

from crit_app_v2.job_stats.models import Role


@dataclass(frozen=True)
class RoleSpec:
    """Labels and behavior that follow directly from a combat role."""

    main_stat_label: str
    main_stat_placeholder: str
    speed_stat_label: str
    speed_stat_placeholder: str
    requires_tenacity: bool


ROLE_SPECS = {
    Role.TANK: RoleSpec(
        main_stat_label="STR",
        main_stat_placeholder="Strength",
        speed_stat_label="SKS",
        speed_stat_placeholder="Skill Speed",
        requires_tenacity=True,
    ),
    Role.HEALER: RoleSpec(
        main_stat_label="MND",
        main_stat_placeholder="Mind",
        speed_stat_label="SPS",
        speed_stat_placeholder="Spell Speed",
        requires_tenacity=False,
    ),
    Role.MELEE: RoleSpec(
        main_stat_label="STR / DEX",
        main_stat_placeholder="Strength / Dexterity",
        speed_stat_label="SKS",
        speed_stat_placeholder="Skill Speed",
        requires_tenacity=False,
    ),
    Role.PHYSICAL_RANGED: RoleSpec(
        main_stat_label="DEX",
        main_stat_placeholder="Dexterity",
        speed_stat_label="SKS",
        speed_stat_placeholder="Skill Speed",
        requires_tenacity=False,
    ),
    Role.MAGICAL_RANGED: RoleSpec(
        main_stat_label="INT",
        main_stat_placeholder="Intelligence",
        speed_stat_label="SPS",
        speed_stat_placeholder="Spell Speed",
        requires_tenacity=False,
    ),
}
