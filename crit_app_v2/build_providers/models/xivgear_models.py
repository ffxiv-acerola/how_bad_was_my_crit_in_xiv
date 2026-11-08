"""Normalized domain models for XIVGear sets and loaded sheets."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from crit_app_v2.build_providers.models.models import (
    BuildProvider,
    BuildUrl,
    RoleBuildStatsModel,
)
from crit_app_v2.game_data.roles import Role


class LoadedXivGearSet(BaseModel):
    """Normalized stats and name for one entry in an XIVGear response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_index: int = Field(ge=0)
    build_name: str
    build_stats: RoleBuildStatsModel


class LoadedXivGearBuild(BaseModel):
    """Normalized data loaded from an XIVGear sheet or set URL."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_provider: Literal[BuildProvider.XIV_GEAR] = BuildProvider.XIV_GEAR
    build_url: BuildUrl
    build_index: int | None = Field(default=None, ge=0)
    build_role: Role
    sets: list[LoadedXivGearSet]
