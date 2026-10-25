"""Unit tests for job-stat draft validation."""

import pytest

from crit_app_v2.job_stats.form_validation import FormStatValue, validate_job_stats_form
from crit_app_v2.job_stats.roles import Role
from crit_app_v2.job_stats.stats import STAT_INPUTS, Stats


@pytest.fixture
def valid_form_stats() -> dict[Stats, FormStatValue]:
    """Return in-range values for every job stat."""
    return {
        Stats.MAIN_STAT: 4000,
        Stats.DETERMINATION: 2000,
        Stats.SPEED_STAT: 800,
        Stats.CRITICAL_HIT: 2500,
        Stats.DIRECT_HIT: 1200,
        Stats.WEAPON_DAMAGE: 140,
        Stats.TENACITY: 1000,
    }


def test_complete_non_tank_form_is_valid_without_tenacity(valid_form_stats):
    """Accept a complete non-Tank form without Tenacity."""
    stats = valid_form_stats
    stats[Stats.TENACITY] = None

    result = validate_job_stats_form(Role.HEALER, stats)

    assert result.is_valid
    assert result.errors[Stats.TENACITY] is None


def test_complete_tank_form_is_valid_with_tenacity(valid_form_stats):
    """Accept a complete Tank form that includes Tenacity."""
    result = validate_job_stats_form(Role.TANK, valid_form_stats)

    assert result.is_valid
    assert result.errors[Stats.TENACITY] is None


def test_fresh_blank_form_is_invalid_without_showing_errors():
    """Keep a fresh incomplete form quiet until a field is edited."""
    stats = dict.fromkeys(Stats)

    result = validate_job_stats_form(Role.TANK, stats)

    assert not result.is_valid
    assert all(error is None for error in result.errors.values())


def test_cleared_required_value_shows_feedback(valid_form_stats):
    """Show required-value feedback after an entered field is cleared."""
    stats = valid_form_stats
    stats[Stats.MAIN_STAT] = ""

    result = validate_job_stats_form(Role.HEALER, stats)

    assert not result.is_valid
    assert result.errors[Stats.MAIN_STAT] == "Please enter a value."


@pytest.mark.parametrize("tenacity", [None, "", 0])
def test_non_tank_ignores_tenacity_value(tenacity, valid_form_stats):
    """Ignore hidden Tenacity values for non-Tank roles."""
    stats = valid_form_stats
    stats[Stats.TENACITY] = tenacity

    result = validate_job_stats_form(Role.HEALER, stats)

    assert result.is_valid
    assert result.errors[Stats.TENACITY] is None


@pytest.mark.parametrize("stat, stat_input", STAT_INPUTS.items())
@pytest.mark.parametrize("boundary", ["lower", "upper"])
def test_form_validation_accepts_inclusive_stat_range_boundaries(stat, stat_input, boundary, valid_form_stats):
    """Accept each stat's inclusive lower and upper bounds."""
    stats = valid_form_stats
    stats[stat] = getattr(stat_input, boundary)

    result = validate_job_stats_form(Role.TANK, stats)

    assert result.is_valid
    assert result.errors[stat] is None


@pytest.mark.parametrize("stat, stat_input", STAT_INPUTS.items())
@pytest.mark.parametrize("offset", [-1, 1])
def test_out_of_range_value_has_error_for_its_stat(stat, stat_input, offset, valid_form_stats):
    """Report an error only for a stat outside its allowed range."""
    stats = valid_form_stats
    stats[stat] = stat_input.lower - 1 if offset < 0 else stat_input.upper + 1

    result = validate_job_stats_form(Role.TANK, stats)

    assert not result.is_valid
    assert result.errors[stat] is not None
    assert all(error is None for key, error in result.errors.items() if key != stat)
