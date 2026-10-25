"""Tests for the framework-independent job-stats domain models."""

import pytest
from pydantic import ValidationError

from crit_app_v2.job_stats.build_provider import BuildProvider
from crit_app_v2.job_stats.models import (
    BuildModel,
    JobStatsModel,
    Role,
)
from crit_app_v2.job_stats.roles import ROLE_SPECS
from crit_app_v2.job_stats.stats import STAT_INPUTS, Stats


def job_stats_data(role=Role.HEALER, stats_overrides=None, **overrides):
    """Return valid nested job-stat input data with optional overrides."""
    data = {
        "role": role,
        "stats": {
            Stats.MAIN_STAT: 4000,
            Stats.DETERMINATION: 2000,
            Stats.SPEED_STAT: 800,
            Stats.CRITICAL_HIT: 2500,
            Stats.DIRECT_HIT: 1200,
            Stats.WEAPON_DAMAGE: 140,
        },
    }
    data.update(overrides)
    if stats_overrides is not None:
        data["stats"].update(stats_overrides)
    return data


def test_job_stats_model_accepts_complete_non_tank_stats():
    """Accept a complete build without the Tank-only Tenacity stat."""
    stats = JobStatsModel.model_validate(job_stats_data())

    assert stats.role is Role.HEALER
    assert Stats.TENACITY not in stats.stats
    assert stats.build is None


def test_job_stats_model_serializes_role_as_a_string():
    """Serialize the role enum as its string value."""
    stats = JobStatsModel.model_validate(job_stats_data())

    assert stats.model_dump(mode="json")["role"] == "Healer"


def test_tank_requires_tenacity():
    """Reject a Tank build that omits Tenacity."""
    with pytest.raises(ValidationError, match="Missing stats"):
        JobStatsModel.model_validate(job_stats_data(role=Role.TANK))


def test_non_tank_rejects_tenacity():
    """Reject Tenacity when it is supplied for a non-Tank role."""
    with pytest.raises(ValidationError, match="Stats not valid"):
        JobStatsModel.model_validate(
            job_stats_data(stats_overrides={Stats.TENACITY: 1000})
        )


def test_tank_accepts_tenacity_in_range():
    """Accept a Tank build with an in-range Tenacity value."""
    stats = JobStatsModel.model_validate(
        job_stats_data(
            role=Role.TANK,
            stats_overrides={Stats.TENACITY: 1000},
        )
    )

    assert stats.stats[Stats.TENACITY] == 1000


@pytest.mark.parametrize("stat, stat_input", STAT_INPUTS.items())
@pytest.mark.parametrize("boundary", ["lower", "upper"])
def test_job_stats_model_accepts_inclusive_stat_range_boundaries(
    stat, stat_input, boundary
):
    """Accept every stat's inclusive lower and upper bounds."""
    value = getattr(stat_input, boundary)
    data = job_stats_data(
        role=Role.TANK,
        stats_overrides={Stats.TENACITY: 1000},
    )
    data["stats"][stat] = value

    model = JobStatsModel.model_validate(data)

    assert model.stats[stat] == value


@pytest.mark.parametrize("stat, stat_input", STAT_INPUTS.items())
@pytest.mark.parametrize("offset", [-1, 1])
def test_job_stats_model_rejects_values_outside_stat_ranges(stat, stat_input, offset):
    """Reject values just outside each stat's canonical range."""
    value = stat_input.lower - 1 if offset < 0 else stat_input.upper + 1
    data = job_stats_data(
        role=Role.TANK,
        stats_overrides={Stats.TENACITY: 1000},
    )
    data["stats"][stat] = value

    with pytest.raises(ValidationError):
        JobStatsModel.model_validate(data)


def test_etro_build_rejects_an_xivgear_selection_index():
    """Reject an XIVGear selection index on an Etro build."""
    with pytest.raises(ValidationError, match="build_index is only valid"):
        BuildModel(
            build_provider=BuildProvider.ETRO,
            build_id="etro-build-id",
            build_index=0,
        )


def test_xivgear_build_accepts_an_optional_selection_index():
    """Accept and serialize an XIVGear selection index."""
    build = BuildModel(
        build_provider=BuildProvider.XIV_GEAR,
        build_id="sl|build-id",
        build_index=2,
    )

    assert build.model_dump(mode="json") == {
        "build_provider": "xivgear.app",
        "build_id": "sl|build-id",
        "build_index": 2,
    }


def test_role_specs_are_complete_and_framework_independent():
    """Ensure role metadata covers roles and Tank-specific behavior."""
    assert set(ROLE_SPECS) == set(Role)
    assert ROLE_SPECS[Role.TANK].requires_tenacity
    assert not ROLE_SPECS[Role.HEALER].requires_tenacity
    assert ROLE_SPECS[Role.HEALER].speed_stat_label == "Spell speed"
