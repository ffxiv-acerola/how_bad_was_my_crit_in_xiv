"""Validated models for Etro API responses."""

from collections import Counter
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from crit_app_v2.build_providers.models.models import (
    BuildProvider,
    BuildUrl,
    RoleBuildStatsModel,
)
from crit_app_v2.game_data.jobs import JOB_SPECS, Job
from crit_app_v2.game_data.roles import ROLE_SPECS, Role
from crit_app_v2.game_data.stats import MAIN_STAT_SPEC, SPEED_STAT_SPEC


class LoadedEtroBuild(BaseModel):
    """Normalized reference to one Etro gearset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_provider: Literal[BuildProvider.ETRO] = BuildProvider.ETRO
    build_url: BuildUrl
    build_id: UUID4
    build_name: str
    build_role: Role

    build_stats: RoleBuildStatsModel


class EtroTotalParam(BaseModel):
    """One named parameter in Etro's ``totalParams`` response list."""

    model_config = ConfigDict(extra="ignore")

    name: str
    value: Any = None


class EtroBuildResponse(BaseModel):
    """The subset of an Etro response needed to load a role build.

    Extra response fields and unrelated ``totalParams`` entries are ignored.
    Required parameters are determined by the response job and its role.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    job: Job = Field(validation_alias="jobAbbrev")
    party_bonus: float = Field(validation_alias="partyBonus", gt=0, allow_inf_nan=False)
    total_params: list[EtroTotalParam] = Field(validation_alias="totalParams")

    def _required_stat_names(self) -> set[str]:
        """Get Etro stat names required for this response's job and role."""
        job_spec = JOB_SPECS[self.job]
        role_spec = ROLE_SPECS[job_spec.role]
        required_names = {
            "DET",
            "CRT",
            "DH",
            "Weapon Damage",
            MAIN_STAT_SPEC[job_spec.main_stat].etro_name,
            SPEED_STAT_SPEC[role_spec.speed_stat].etro_name,
        }
        if role_spec.requires_tenacity:
            required_names.add("TEN")
        return required_names

    @model_validator(mode="after")
    def validate_required_stats(self) -> "EtroBuildResponse":
        """Ensure every stat needed by this job and role is present once."""
        required_names = self._required_stat_names()

        counts = Counter(param.name for param in self.total_params)
        missing = required_names - counts.keys()
        duplicates = {name for name in required_names if counts[name] > 1}
        if missing or duplicates:
            problems = []
            if missing:
                problems.append(f"missing required stats: {sorted(missing)}")
            if duplicates:
                problems.append(f"duplicate required stats: {sorted(duplicates)}")
            raise ValueError("Etro totalParams has " + "; ".join(problems))

        invalid_values = [
            param.name
            for param in self.total_params
            if param.name in required_names and type(param.value) is not int
        ]
        if invalid_values:
            raise ValueError(
                f"Etro required stat values must be integers: {sorted(invalid_values)}"
            )

        return self

    @property
    def required_stats(self) -> dict[str, int]:
        """Return the validated subset of parameters used for processing."""
        required_names = self._required_stat_names()
        return {
            param.name: param.value
            for param in self.total_params
            if param.name in required_names
        }
