"""Validated domain models for entered job statistics and external builds."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from crit_app_v2.job_stats.ranges import STAT_RANGES


class Role(StrEnum):
    """The supported FFXIV combat roles for entered job statistics."""

    TANK = "Tank"
    HEALER = "Healer"
    MELEE = "Melee"
    PHYSICAL_RANGED = "Physical Ranged"
    MAGICAL_RANGED = "Magical Ranged"


class BuildProvider(StrEnum):
    """External build providers supported by the application."""

    ETRO = "etro.gg"
    XIV_GEAR = "xivgear.app"


class BuildModel(BaseModel):
    """The persisted identity of an externally loaded job build."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    build_provider: BuildProvider
    build_id: str = Field(min_length=1)
    build_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_build_index(self) -> "BuildModel":
        """Allow a selected build index only for XIVGear sheets."""
        if self.build_provider is BuildProvider.ETRO and self.build_index is not None:
            raise ValueError("build_index is only valid for xivgear.app builds")
        return self


class JobStatsModel(BaseModel):
    """A complete, validated set of user-entered job statistics.

    Concrete job selection and party-bonus calculations occur later in the
    analysis workflow, so they do not belong to this input model.
    """

    model_config = ConfigDict(extra="forbid")

    role: Role
    main_stat: int = Field(
        ge=STAT_RANGES["main_stat"].lower,
        le=STAT_RANGES["main_stat"].upper,
    )
    determination: int = Field(
        ge=STAT_RANGES["determination"].lower,
        le=STAT_RANGES["determination"].upper,
    )
    speed_stat: int = Field(
        ge=STAT_RANGES["speed_stat"].lower,
        le=STAT_RANGES["speed_stat"].upper,
    )
    critical_hit: int = Field(
        ge=STAT_RANGES["critical_hit"].lower,
        le=STAT_RANGES["critical_hit"].upper,
    )
    direct_hit: int = Field(
        ge=STAT_RANGES["direct_hit"].lower,
        le=STAT_RANGES["direct_hit"].upper,
    )
    weapon_damage: int = Field(
        ge=STAT_RANGES["weapon_damage"].lower,
        le=STAT_RANGES["weapon_damage"].upper,
    )
    tenacity: int | None = Field(
        default=None,
        ge=STAT_RANGES["tenacity"].lower,
        le=STAT_RANGES["tenacity"].upper,
    )
    build: BuildModel | None = None

    @model_validator(mode="after")
    def validate_tenacity(self) -> "JobStatsModel":
        """Require Tenacity for Tanks and reject it for every other role."""
        if self.role is Role.TANK and self.tenacity is None:
            raise ValueError("Tenacity is required for Tank builds")
        if self.role is not Role.TANK and self.tenacity is not None:
            raise ValueError("Tenacity is only valid for Tank builds")
        return self
