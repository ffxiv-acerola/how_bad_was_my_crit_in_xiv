"""Framework-independent job identifiers and provider reference metadata."""

from dataclasses import dataclass
from enum import StrEnum

from crit_app_v2.game_data.roles import Role
from crit_app_v2.game_data.stats import MainStats


class Job(StrEnum):
    """Supported playable jobs, represented by canonical provider names."""

    WHITE_MAGE = "WhiteMage"
    SCHOLAR = "Scholar"
    ASTROLOGIAN = "Astrologian"
    SAGE = "Sage"
    PALADIN = "Paladin"
    WARRIOR = "Warrior"
    DARK_KNIGHT = "DarkKnight"
    GUNBREAKER = "Gunbreaker"
    DRAGOON = "Dragoon"
    REAPER = "Reaper"
    MONK = "Monk"
    SAMURAI = "Samurai"
    NINJA = "Ninja"
    VIPER = "Viper"
    BARD = "Bard"
    MACHINIST = "Machinist"
    DANCER = "Dancer"
    BLACK_MAGE = "BlackMage"
    SUMMONER = "Summoner"
    RED_MAGE = "RedMage"
    PICTOMANCER = "Pictomancer"

    @classmethod
    def _missing_(cls, value: object) -> "Job | None":
        """Resolve provider-specific job abbreviations when possible.

        Parameters
        ----------
        value
            Value that failed normal enum lookup.

        Returns
        -------
        Job or None
            Matching job for a recognized Etro or XIVGear abbreviation, or
            ``None`` when the value is unsupported.
        """
        if not isinstance(value, str):
            return None

        # Cutesy way to allow other representations of the job name
        # e.g., WHM
        for job, spec in JOB_SPECS.items():
            if value in (spec.etro_name, spec.xivgear_name):
                return job

        return None


@dataclass(frozen=True)
class JobSpec:
    """Provider names and stat metadata associated with one job.

    Parameters
    ----------
    job
        Canonical job identifier represented by this specification.
    etro_name
        Job abbreviation used in Etro responses.
    xivgear_name
        Job identifier used in XIVGear responses.
    fflogs_name
        Canonical job name used by FFLogs.
    display_name
        Human-readable job name.
    role
        Combat role used to resolve role-level stat requirements.
    main_stat
        Main-stat category used by the job.
    weapon_delay
        Job weapon delay in seconds.
    """

    job: Job
    etro_name: str
    xivgear_name: str
    fflogs_name: str
    display_name: str
    role: Role
    main_stat: MainStats
    weapon_delay: float


JOB_SPECS = {
    Job.WHITE_MAGE: JobSpec(
        Job.WHITE_MAGE,
        etro_name="WHM",
        xivgear_name="WHM",
        fflogs_name="WhiteMage",
        display_name="White Mage",
        role=Role.HEALER,
        main_stat=MainStats.MIND,
        weapon_delay=3.44,
    ),
    Job.SCHOLAR: JobSpec(
        Job.SCHOLAR,
        etro_name="SCH",
        xivgear_name="SCH",
        fflogs_name="Scholar",
        display_name="Scholar",
        role=Role.HEALER,
        main_stat=MainStats.MIND,
        weapon_delay=3.12,
    ),
    Job.ASTROLOGIAN: JobSpec(
        Job.ASTROLOGIAN,
        etro_name="AST",
        xivgear_name="AST",
        fflogs_name="Astrologian",
        display_name="Astrologian",
        role=Role.HEALER,
        main_stat=MainStats.MIND,
        weapon_delay=3.20,
    ),
    Job.SAGE: JobSpec(
        Job.SAGE,
        etro_name="SGE",
        xivgear_name="SGE",
        fflogs_name="Sage",
        display_name="Sage",
        role=Role.HEALER,
        main_stat=MainStats.MIND,
        weapon_delay=2.80,
    ),
    Job.PALADIN: JobSpec(
        Job.PALADIN,
        etro_name="PLD",
        xivgear_name="PLD",
        fflogs_name="Paladin",
        display_name="Paladin",
        role=Role.TANK,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.24,
    ),
    Job.WARRIOR: JobSpec(
        Job.WARRIOR,
        etro_name="WAR",
        xivgear_name="WAR",
        fflogs_name="Warrior",
        display_name="Warrior",
        role=Role.TANK,
        main_stat=MainStats.STRENGTH,
        weapon_delay=3.36,
    ),
    Job.DARK_KNIGHT: JobSpec(
        Job.DARK_KNIGHT,
        etro_name="DRK",
        xivgear_name="DRK",
        fflogs_name="DarkKnight",
        display_name="Dark Knight",
        role=Role.TANK,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.96,
    ),
    Job.GUNBREAKER: JobSpec(
        Job.GUNBREAKER,
        etro_name="GNB",
        xivgear_name="GNB",
        fflogs_name="Gunbreaker",
        display_name="Gunbreaker",
        role=Role.TANK,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.80,
    ),
    Job.DRAGOON: JobSpec(
        Job.DRAGOON,
        etro_name="DRG",
        xivgear_name="DRG",
        fflogs_name="Dragoon",
        display_name="Dragoon",
        role=Role.MELEE,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.80,
    ),
    Job.REAPER: JobSpec(
        Job.REAPER,
        etro_name="RPR",
        xivgear_name="RPR",
        fflogs_name="Reaper",
        display_name="Reaper",
        role=Role.MELEE,
        main_stat=MainStats.STRENGTH,
        weapon_delay=3.20,
    ),
    Job.MONK: JobSpec(
        Job.MONK,
        etro_name="MNK",
        xivgear_name="MNK",
        fflogs_name="Monk",
        display_name="Monk",
        role=Role.MELEE,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.56,
    ),
    Job.SAMURAI: JobSpec(
        Job.SAMURAI,
        etro_name="SAM",
        xivgear_name="SAM",
        fflogs_name="Samurai",
        display_name="Samurai",
        role=Role.MELEE,
        main_stat=MainStats.STRENGTH,
        weapon_delay=2.64,
    ),
    Job.NINJA: JobSpec(
        Job.NINJA,
        etro_name="NIN",
        xivgear_name="NIN",
        fflogs_name="Ninja",
        display_name="Ninja",
        role=Role.MELEE,
        main_stat=MainStats.DEXTERITY,
        weapon_delay=2.56,
    ),
    Job.VIPER: JobSpec(
        Job.VIPER,
        etro_name="VPR",
        xivgear_name="VPR",
        fflogs_name="Viper",
        display_name="Viper",
        role=Role.MELEE,
        main_stat=MainStats.DEXTERITY,
        weapon_delay=2.64,
    ),
    Job.BARD: JobSpec(
        Job.BARD,
        etro_name="BRD",
        xivgear_name="BRD",
        fflogs_name="Bard",
        display_name="Bard",
        role=Role.PHYSICAL_RANGED,
        main_stat=MainStats.DEXTERITY,
        weapon_delay=3.04,
    ),
    Job.MACHINIST: JobSpec(
        Job.MACHINIST,
        etro_name="MCH",
        xivgear_name="MCH",
        fflogs_name="Machinist",
        display_name="Machinist",
        role=Role.PHYSICAL_RANGED,
        main_stat=MainStats.DEXTERITY,
        weapon_delay=2.64,
    ),
    Job.DANCER: JobSpec(
        Job.DANCER,
        etro_name="DNC",
        xivgear_name="DNC",
        fflogs_name="Dancer",
        display_name="Dancer",
        role=Role.PHYSICAL_RANGED,
        main_stat=MainStats.DEXTERITY,
        weapon_delay=3.12,
    ),
    Job.BLACK_MAGE: JobSpec(
        Job.BLACK_MAGE,
        etro_name="BLM",
        xivgear_name="BLM",
        fflogs_name="BlackMage",
        display_name="Black Mage",
        role=Role.MAGICAL_RANGED,
        main_stat=MainStats.INTELLIGENCE,
        weapon_delay=3.28,
    ),
    Job.SUMMONER: JobSpec(
        Job.SUMMONER,
        etro_name="SMN",
        xivgear_name="SMN",
        fflogs_name="Summoner",
        display_name="Summoner",
        role=Role.MAGICAL_RANGED,
        main_stat=MainStats.INTELLIGENCE,
        weapon_delay=3.12,
    ),
    Job.RED_MAGE: JobSpec(
        Job.RED_MAGE,
        etro_name="RDM",
        xivgear_name="RDM",
        fflogs_name="RedMage",
        display_name="Red Mage",
        role=Role.MAGICAL_RANGED,
        main_stat=MainStats.INTELLIGENCE,
        weapon_delay=3.44,
    ),
    Job.PICTOMANCER: JobSpec(
        Job.PICTOMANCER,
        etro_name="PCT",
        xivgear_name="PCT",
        fflogs_name="Pictomancer",
        display_name="Pictomancer",
        role=Role.MAGICAL_RANGED,
        main_stat=MainStats.INTELLIGENCE,
        weapon_delay=2.96,
    ),
}
