"""Validated domain models for entered job statistics and external builds."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from crit_app_v2.job_stats.build_provider import BuildProvider
from crit_app_v2.job_stats.roles import Role
from crit_app_v2.job_stats.stats import STAT_INPUTS, Stats


class BuildModel(BaseModel):
    """The persisted identity of an externally loaded job build."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    build_provider: BuildProvider
    build_id: str = Field(min_length=1)
    build_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_build_index(self) -> "BuildModel":
        """Ensure build indices are only used with XIVGear builds.

        Returns
        -------
        BuildModel
            The validated build model.

        Raises
        ------
        ValueError
            If an Etro build includes a selection index.
        """
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
    stats: dict[Stats, int]
    build: BuildModel | None = None

    @model_validator(mode="after")
    def check_ranges(self) -> "JobStatsModel":
        """Ensure every entered stat is within its allowed range.

        Returns
        -------
        JobStatsModel
            The validated job-stats model.

        Raises
        ------
        ValueError
            If any stat is outside its allowed range.
        """
        for stat, value in self.stats.items():
            r = STAT_INPUTS[stat]
            if not r.lower <= value <= r.upper:
                raise ValueError(f"{stat} must be in {r.placeholder_text()}")
        return self

    @model_validator(mode="after")
    def check_required_stats(self) -> "JobStatsModel":
        """Ensure stats match the selected role's requirements.

        Returns
        -------
        JobStatsModel
            The validated job-stats model.

        Raises
        ------
        ValueError
            If required stats are missing or role-incompatible stats exist.
        """
        expected = set(Stats)
        if self.role is not Role.TANK:
            expected.discard(Stats.TENACITY)

        missing = expected - self.stats.keys()
        extra = self.stats.keys() - expected
        if missing:
            raise ValueError(f"Missing stats: {sorted(missing)}")
        if extra:
            raise ValueError(f"Stats not valid for {self.role}: {sorted(extra)}")
        return self
