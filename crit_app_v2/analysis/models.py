"""Validated models used to prepare player and party analysis inputs."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from crit_app_v2.build_providers.models import ValidatedRoleBuild
from crit_app_v2.fflogs_encounters.models import Encounter, EncounterPersonnel
from crit_app_v2.game_data import JOB_SPECS, Job, Role


class PlayerAnalysisStats(BaseModel):
    """Analysis metadata composed with a validated role build."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    job: Job
    build: ValidatedRoleBuild
    party_bonus: float

    @model_validator(mode="after")
    def validate_build(self) -> "PlayerAnalysisStats":
        """Ensure the selected job matches the validated role build."""
        job_spec = JOB_SPECS[self.job]
        if job_spec.role is not self.build.role:
            raise ValueError(f"{self.job.value} is not a {self.build.role.value} job.")
        return self

    @property
    def role(self) -> Role:
        """Return the role from the validated build."""
        return self.build.role

    @property
    def main_stat_pre_bonus(self) -> int:
        """Return the entered main-stat value before party bonus."""
        return self.build.stats.main_stat

    @property
    def main_stat(self) -> int:
        """Return the main stat after applying the party composition bonus."""
        return int(self.main_stat_pre_bonus * self.party_bonus)

    @property
    def main_stat_type(self) -> str:
        """Return the canonical main-stat identifier for this job."""
        return JOB_SPECS[self.job].main_stat.value

    @property
    def determination(self) -> int:
        """Return the validated Determination value."""
        return self.build.stats.determination

    @property
    def speed_stat(self) -> int:
        """Return the validated role-specific speed-stat value."""
        return self.build.stats.speed_stat

    @property
    def critical_hit(self) -> int:
        """Return the validated Critical Hit value."""
        return self.build.stats.critical_hit

    @property
    def direct_hit(self) -> int:
        """Return the validated Direct Hit value."""
        return self.build.stats.direct_hit

    @property
    def weapon_damage(self) -> int:
        """Return the validated weapon-damage value."""
        return self.build.stats.weapon_damage

    @property
    def tenacity(self) -> int | None:
        """Return validated Tenacity for Tanks, or None for other roles."""
        return self.build.stats.tenacity

    @property
    def secondary_stat_pre_bonus(self) -> int | None:
        """Return the entered Tenacity for Tanks, or None for other roles."""
        return self.build.stats.tenacity

    @property
    def secondary_stat(self) -> int | None:
        """Return the secondary stat used by the current player analysis."""
        return self.build.stats.tenacity

    @property
    def secondary_stat_type(self) -> str | None:
        """Return Tenacity for Tanks and None for non-Tank roles."""
        return "tenacity" if self.build.role is Role.TANK else None

    @property
    def delay(self) -> float:
        """Return the weapon delay from canonical job reference data."""
        return JOB_SPECS[self.job].weapon_delay


class PreparedPlayerAnalysis(BaseModel):
    """Validated context ready to pass to the rotation-analysis stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    encounter: Encounter
    player: EncounterPersonnel
    phase_id: int = Field(ge=0)
    encounter_level: int = Field(gt=0)
    stats: PlayerAnalysisStats

    @model_validator(mode="after")
    def validate_selection(self) -> "PreparedPlayerAnalysis":
        """Ensure the selected player belongs to the validated encounter."""
        if self.player not in self.encounter.players:
            raise ValueError("The selected player is not part of this encounter.")
        if (
            self.player.job is not self.stats.job
            or self.player.role is not self.stats.role
        ):
            raise ValueError("The selected player's job and role must match the stats.")
        return self
