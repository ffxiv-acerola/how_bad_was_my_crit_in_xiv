"""Validate incomplete job-stat form drafts without weakening domain models."""

from dataclasses import dataclass
from typing import Literal, Mapping

from crit_app_v2.game_data import STAT_INPUTS, Role, Stats

FormStatValue = int | Literal[""] | None


@dataclass(frozen=True)
class StatValidation:
    """Result of validating one entered statistic.

    Parameters
    ----------
    is_valid
        Whether the stat is valid for a complete build.
    error
        User-facing range or required-value error, or ``None`` when no error is
        shown.
    """

    is_valid: bool
    error: str | None


@dataclass(frozen=True)
class JobStatsFormValidation:
    """Validation feedback for a job-stat form draft.

    Parameters
    ----------
    is_valid
        Whether all required statistics form a valid complete build.
    errors
        User-facing errors keyed by statistic.
    """

    is_valid: bool
    errors: Mapping[Stats, str | None]


def _stat_validator(
    stat_value: FormStatValue,
    stat_to_validate: Stats,
    role: Role,
) -> StatValidation:
    """Validate one statistic from a job-stat form draft.

    Parameters
    ----------
    stat_value
        Entered value, ``None`` for an untouched field, or ``""`` when cleared.
    stat_to_validate
        Statistic represented by the input field.
    role
        Selected combat role, used for the Tenacity requirement.

    Returns
    -------
    StatValidation
        Validity and any range error to display for the statistic.
    """
    # Ignore hidden Tenacity values for non-Tanks, including stale UI state.
    if stat_to_validate is Stats.TENACITY and role is not Role.TANK:
        return StatValidation(is_valid=True, error=None)

    if stat_value == "":
        return StatValidation(is_valid=False, error="Please enter a value.")

    if stat_value is not None:
        stat_range = STAT_INPUTS[stat_to_validate]
        is_valid = stat_range.lower <= stat_value <= stat_range.upper
        error = None
        if not is_valid:
            error = (
                f"{stat_to_validate} must be between "
                f"{stat_range.lower} - {stat_range.upper}."
            )
        return StatValidation(is_valid=is_valid, error=error)

    return StatValidation(is_valid=False, error=None)


def validate_job_stats_form(
    role_value: Role, stats: Mapping[Stats, FormStatValue]
) -> JobStatsFormValidation:
    """Validate the current job-stat form values.

    Blank required fields (``None``) make the form invalid but do not display
    an error. Cleared fields (``""``) display a required-value error. Tenacity
    is ignored for non-Tank roles.

    Parameters
    ----------
    role_value
        Selected combat role.
    stats
        Current integer, blank, or cleared values keyed by statistic.

    Returns
    -------
    JobStatsFormValidation
        Complete-form validity and field errors keyed by statistic.
    """
    stat_results: dict[Stats, StatValidation] = {
        stat: _stat_validator(stats[stat], stat, role_value) for stat in Stats
    }

    errors = {stat: result.error for stat, result in stat_results.items()}
    return JobStatsFormValidation(
        is_valid=all(result.is_valid for result in stat_results.values()),
        errors=errors,
    )
