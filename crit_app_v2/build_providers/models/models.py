"""Shared provider identifiers, URLs, and role-level build models."""

from enum import StrEnum
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, BaseModel, ConfigDict
from pydantic.functional_validators import model_validator

from crit_app_v2.game_data.roles import Role


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


class InternalBuild(BaseModel):
    """Role-level build selected from the site's internal build manager."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_provider: Literal[BuildProvider.INTERNAL] = BuildProvider.INTERNAL
    build_role: Role
    build_name: str

    build_stats: RoleBuildStatsModel


# TODO handle later, isn't needed just yet
# class JobStatsModel(BaseModel):
#     """A complete, validated set of user-entered job statistics.
#
#     Concrete job selection and party-bonus calculations occur later in the
#     analysis workflow, so they do not belong to this input model.
#     """
#
#     model_config = ConfigDict(extra="forbid")
#
#     role: Role
#     stats: dict[Stats, int]
#     build: ProviderStatsModel | None = None
#
#     @model_validator(mode="after")
#     def check_ranges(self) -> "JobStatsModel":
#         """Ensure every entered stat is within its allowed range.
#
#         Returns
#         -------
#         JobStatsModel
#             The validated job-stats model.
#
#         Raises
#         ------
#         ValueError
#             If any stat is outside its allowed range.
#         """
#         for stat, value in self.stats.items():
#             r = STAT_INPUTS[stat]
#             if not r.lower <= value <= r.upper:
#                 raise ValueError(f"{stat} must be in {r.placeholder_text()}")
#         return self
#
#     @model_validator(mode="after")
#     def check_required_stats(self) -> "JobStatsModel":
#         """Ensure stats match the selected role's requirements.
#
#         Returns
#         -------
#         JobStatsModel
#             The validated job-stats model.
#
#         Raises
#         ------
#         ValueError
#             If required stats are missing or role-incompatible stats exist.
#         """
#         expected = set(Stats)
#         if self.role is not Role.TANK:
#             expected.discard(Stats.TENACITY)
#
#         missing = expected - self.stats.keys()
#         extra = self.stats.keys() - expected
#         if missing:
#             raise ValueError(f"Missing stats: {sorted(missing)}")
#         if extra:
#             raise ValueError(f"Stats not valid for {self.role}: {sorted(extra)}")
#         return self
