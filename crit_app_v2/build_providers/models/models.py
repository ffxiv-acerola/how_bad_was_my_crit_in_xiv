"""Shared provider identifiers, URLs, and role-level build models."""

from enum import StrEnum
from typing import ClassVar, Literal, Self
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, BaseModel, ConfigDict
from pydantic.functional_validators import model_validator

from crit_app_v2.game_data import STAT_INPUTS, Role, Stats


class BuildProvider(StrEnum):
    """Known build origins, including the site's internal build manager."""

    ETRO = "etro.gg"
    XIV_GEAR = "xivgear.app"
    INTERNAL = "internal"


class BuildUrl(BaseModel):
    """A user-supplied URL for a supported external build provider."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    build_url: AnyHttpUrl

    @model_validator(mode="after")
    def validate_provider(self) -> Self:
        """Ensure the URL belongs to a supported build provider.

        Returns
        -------
        Self
            The validated build URL model.

        Raises
        ------
        ValueError
            If the URL host is not a supported provider.
        """
        _ = self._provider_from_url()
        return self

    def _provider_from_url(self) -> BuildProvider:
        """Classify the URL using its hostname.

        Returns
        -------
        BuildProvider
            Provider associated with the URL host.

        Raises
        ------
        ValueError
            If the URL host is not a supported provider.
        """
        parsed_url = urlparse(str(self.build_url))
        hostname = parsed_url.hostname.lower() if parsed_url.hostname else ""

        provider_by_host = {
            "etro.gg": BuildProvider.ETRO,
            "www.etro.gg": BuildProvider.ETRO,
            "xivgear.app": BuildProvider.XIV_GEAR,
            "www.xivgear.app": BuildProvider.XIV_GEAR,
            "share.xivgear.app": BuildProvider.XIV_GEAR,
        }

        try:
            return provider_by_host[hostname]
        except KeyError as error:
            raise ValueError(
                "Only etro.gg or xivgear.app build URLs are supported."
            ) from error

    @property
    def build_provider(self) -> BuildProvider:
        """Return the provider derived from the validated URL host."""
        return self._provider_from_url()


class RoleBuildStatsModel(BaseModel):
    """Complete role-level stat values associated with a build."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    main_stat: int
    determination: int
    speed_stat: int
    critical_hit: int
    direct_hit: int
    weapon_damage: int
    tenacity: int | None


class ValidatedRoleBuild(BaseModel):
    """Complete role build with canonical ranges and Tenacity rules."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    role: Role
    stats: RoleBuildStatsModel

    @model_validator(mode="after")
    def validate_stats(self) -> Self:
        """Check canonical stat ranges and whether Tenacity applies to the role.

        Returns
        -------
        Self
            The validated role build.

        Raises
        ------
        ValueError
            If a stat is outside its canonical range or Tenacity does not match
            the selected role.
        """
        values = {
            Stats.MAIN_STAT: self.stats.main_stat,
            Stats.DETERMINATION: self.stats.determination,
            Stats.SPEED_STAT: self.stats.speed_stat,
            Stats.CRITICAL_HIT: self.stats.critical_hit,
            Stats.DIRECT_HIT: self.stats.direct_hit,
            Stats.WEAPON_DAMAGE: self.stats.weapon_damage,
        }
        if self.role is Role.TANK:
            if self.stats.tenacity is None:
                raise ValueError("Tanks require a Tenacity value.")
            values[Stats.TENACITY] = self.stats.tenacity
        elif self.stats.tenacity is not None:
            raise ValueError("Non-Tanks must not provide Tenacity.")

        for stat, value in values.items():
            limits = STAT_INPUTS[stat]
            if not limits.lower <= value <= limits.upper:
                raise ValueError(
                    f"{stat.value} must be between {limits.lower} and {limits.upper}."
                )
        return self


class InternalBuild(BaseModel):
    """Role-level build selected from the site's internal build manager."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_provider: Literal[BuildProvider.INTERNAL] = BuildProvider.INTERNAL
    build_role: Role
    build_name: str

    build_stats: RoleBuildStatsModel
