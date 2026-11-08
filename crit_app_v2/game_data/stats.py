"""Canonical stat limits for entered job statistics."""

from dataclasses import dataclass
from enum import StrEnum


class Stats(StrEnum):
    """Role-level stat fields collected for a build."""

    MAIN_STAT = "main_stat"
    DETERMINATION = "determination"
    SPEED_STAT = "speed_stat"
    CRITICAL_HIT = "critical_hit"
    DIRECT_HIT = "direct_hit"
    WEAPON_DAMAGE = "weapon_damage"
    TENACITY = "tenacity"


class MainStats(StrEnum):
    """Main-stat categories used by playable jobs."""

    MIND = "mind"
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    INTELLIGENCE = "intelligence"


class SpeedStats(StrEnum):
    """Speed-stat categories selected by combat role."""

    SKILL_SPEED = "skill_speed"
    SPELL_SPEED = "spell_speed"


@dataclass(frozen=True)
class StatInput:
    """Inclusive limits for a numeric job stat.

    Parameters
    ----------
    stat_name
        Domain identifier for this input field.
    lower
        Inclusive minimum accepted value.
    upper
        Inclusive maximum accepted value.
    """

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


@dataclass(frozen=True)
class MainStatSpec:
    """Provider names and display label for a main-stat category.

    Parameters
    ----------
    main_stat
        Domain identifier for the main-stat category.
    fflogs_name
        Field name used by FFLogs.
    etro_name
        Field name used by Etro.
    xivgear_name
        Field name used by XIVGear.
    display_name
        Human-readable label for the stat.
    """

    main_stat: MainStats
    fflogs_name: str
    etro_name: str
    xivgear_name: str
    display_name: str


@dataclass(frozen=True)
class SpeedStatSpec:
    """Provider names and display label for a role's speed stat.

    Parameters
    ----------
    etro_name
        Field name used by Etro.
    xivgear_name
        Field name used by XIVGear.
    display_name
        Human-readable label for the stat.
    """

    etro_name: str
    xivgear_name: str
    display_name: str


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


MAIN_STAT_SPEC = {
    MainStats.MIND: MainStatSpec(
        main_stat=MainStats.MIND,
        fflogs_name="mind",
        etro_name="MND",
        xivgear_name="mind",
        display_name="Mind",
    ),
    MainStats.STRENGTH: MainStatSpec(
        main_stat=MainStats.STRENGTH,
        fflogs_name="strength",
        etro_name="STR",
        xivgear_name="strength",
        display_name="Strength",
    ),
    MainStats.DEXTERITY: MainStatSpec(
        main_stat=MainStats.DEXTERITY,
        fflogs_name="dexterity",
        etro_name="DEX",
        xivgear_name="dexterity",
        display_name="Dexterity",
    ),
    MainStats.INTELLIGENCE: MainStatSpec(
        main_stat=MainStats.INTELLIGENCE,
        fflogs_name="intelligence",
        etro_name="INT",
        xivgear_name="intelligence",
        display_name="Intelligence",
    ),
}

SPEED_STAT_SPEC = {
    SpeedStats.SKILL_SPEED: SpeedStatSpec(
        etro_name="SKS", xivgear_name="skillspeed", display_name="Skill speed"
    ),
    SpeedStats.SPELL_SPEED: SpeedStatSpec(
        etro_name="SPS", xivgear_name="spellspeed", display_name="Spell speed"
    ),
}
