"""Validated and compact DPS distribution data for player analyses."""

from collections.abc import Mapping
from typing import ClassVar, Protocol, cast

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FloatArray = npt.NDArray[np.float64]


def _validated_array(value: object) -> FloatArray:
    """Convert array-like input to a finite, one-dimensional float array."""
    array = cast(FloatArray, np.asarray(value, dtype=np.float64))
    if array.ndim != 1:
        raise ValueError("Distribution arrays must be one-dimensional.")
    if not np.isfinite(array).all():
        raise ValueError("Distribution arrays must contain only finite values.")
    if len(array) < 2:
        raise ValueError("Distribution arrays must contain at least two values.")
    return array


def _reduce_distribution(
    distribution: FloatArray, support: FloatArray, size: int
) -> tuple[FloatArray, FloatArray]:
    """Interpolate a distribution onto a smaller, evenly spaced support."""
    if len(distribution) != len(support):
        raise ValueError("Distribution and support arrays must have equal lengths.")
    if np.any(np.diff(support) <= 0):
        raise ValueError("Distribution support must be strictly increasing.")
    if len(support) <= size:
        return distribution.copy(), support.copy()
    reduced_support = cast(FloatArray, np.linspace(support[0], support[-1], num=size))
    reduced_distribution = cast(
        FloatArray, np.interp(reduced_support, support, distribution)
    )
    return reduced_distribution, reduced_support


class ActionDistributionInput(Protocol):
    """Raw array mapping required from one action distribution."""

    def __getitem__(self, key: str) -> object:
        """Return a raw support or density array by name."""


class JobAnalysisResult(Protocol):
    """Distribution fields consumed from an ``ffxiv_stats`` result."""

    t: float
    rotation_mean: float
    rotation_variance: float
    rotation_std: float
    rotation_skewness: float
    rotation_dps_distribution: FloatArray
    rotation_dps_support: FloatArray
    unique_actions_distribution: Mapping[str, ActionDistributionInput]


class ActionDistribution(BaseModel):
    """Compact probability distribution for one unique action."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)
    support: FloatArray
    dps_distribution: FloatArray
    _array_size: ClassVar[int] = 5000

    @field_validator("support", "dps_distribution", mode="before")
    @classmethod
    def validate_array(cls, value: object) -> FloatArray:
        """Validate array shape and reject NaN or infinite values."""
        return _validated_array(value)

    @model_validator(mode="after")
    def reduce_arrays(self) -> "ActionDistribution":
        """Validate paired arrays and retain only their compact representation."""
        distribution, support = _reduce_distribution(
            self.dps_distribution, self.support, self._array_size
        )
        self.dps_distribution = distribution
        self.support = support
        return self


class PlayerDpsDistribution(BaseModel):
    """Analysis statistics and compact DPS distributions for one player."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        arbitrary_types_allowed=True, extra="forbid"
    )

    active_dps_t: float = Field(gt=0, allow_inf_nan=False)
    analysis_t: float = Field(gt=0, allow_inf_nan=False)
    rotation_mean: float = Field(allow_inf_nan=False)
    rotation_variance: float = Field(ge=0, allow_inf_nan=False)
    rotation_std: float = Field(ge=0, allow_inf_nan=False)
    rotation_skewness: float = Field(allow_inf_nan=False)
    rotation_dps_distribution: FloatArray
    rotation_dps_support: FloatArray
    unique_actions_distribution: dict[str, ActionDistribution]

    _rotation_array_size: ClassVar[int] = 5000

    @field_validator("rotation_dps_distribution", "rotation_dps_support", mode="before")
    @classmethod
    def validate_rotation_array(cls, value: object) -> FloatArray:
        """Validate rotation array shape and reject NaN or infinite values."""
        return _validated_array(value)

    @model_validator(mode="after")
    def reduce_rotation_arrays(self) -> "PlayerDpsDistribution":
        """Validate paired rotation arrays and retain their compact representation."""
        distribution, support = _reduce_distribution(
            self.rotation_dps_distribution,
            self.rotation_dps_support,
            self._rotation_array_size,
        )
        self.rotation_dps_distribution = distribution
        self.rotation_dps_support = support
        return self

    @classmethod
    def from_job_analysis(
        cls, job_analysis: object, active_dps_time: float
    ) -> "PlayerDpsDistribution":
        """Create a compact model from an ``ffxiv_stats`` rotation result.

        Parameters
        ----------
        job_analysis
            Result returned by the role-specific ``ffxiv_stats`` job analysis.
        active_dps_time
            Duration used to normalize the observed DPS.

        Returns
        -------
        PlayerDpsDistribution
            Validated model containing only interpolated distribution arrays.

        Raises
        ------
        ValueError
            If the result contains invalid, mismatched, or non-finite arrays.
        """
        result = cast(JobAnalysisResult, job_analysis)
        action_distributions: dict[str, ActionDistribution] = {}
        for action, values in result.unique_actions_distribution.items():
            action_distributions[action] = ActionDistribution(
                support=_validated_array(values["support"]),
                dps_distribution=_validated_array(values["dps_distribution"]),
            )
        return cls(
            active_dps_t=active_dps_time,
            analysis_t=result.t,
            rotation_mean=result.rotation_mean,
            rotation_variance=result.rotation_variance,
            rotation_std=result.rotation_std,
            rotation_skewness=result.rotation_skewness,
            rotation_dps_distribution=result.rotation_dps_distribution,
            rotation_dps_support=result.rotation_dps_support,
            unique_actions_distribution=action_distributions,
        )


def get_dps_percentile(
    dps: float, distribution: FloatArray, support: FloatArray
) -> float:
    """Return the percentile rank of a DPS value in a sampled PDF.

    Parameters
    ----------
    dps
        DPS value whose percentile is requested.
    distribution
        Probability density values sampled over ``support``.
    support
        Increasing DPS values corresponding to the PDF samples.

    Returns
    -------
    float
        Percentile in the range from 0 to 100.
    """
    if len(distribution) != len(support) or len(support) < 2:
        raise ValueError(
            "Distribution and support must have equal lengths of at least two."
        )
    dx = float(support[1] - support[0])
    if dx <= 0 or not np.isfinite(distribution).all():
        raise ValueError(
            "Distribution support and values must be finite and increasing."
        )
    cumulative = cast(FloatArray, np.cumsum(distribution) * dx)
    index = int(np.abs(support - dps).argmin())
    return float(cumulative[index] * 100)
