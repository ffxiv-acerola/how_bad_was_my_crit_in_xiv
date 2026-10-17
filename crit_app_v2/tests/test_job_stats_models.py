"""Tests for the framework-independent job-stats domain models."""

import pytest
from pydantic import ValidationError

from crit_app_v2.job_stats.models import (
    BuildModel,
    BuildProvider,
    JobStatsModel,
    Role,
)
from crit_app_v2.job_stats.roles import ROLE_SPECS


def job_stats_data(**overrides):
    """Return valid non-Tank form data, allowing one-field overrides."""
    data = {
        "role": Role.HEALER,
        "main_stat": 4000,
        "determination": 2000,
        "speed_stat": 800,
        "critical_hit": 2500,
        "direct_hit": 1200,
        "weapon_damage": 140,
    }
    data.update(overrides)
    return data


def test_job_stats_model_accepts_complete_non_tank_stats():
    stats = JobStatsModel.model_validate(job_stats_data())

    assert stats.role is Role.HEALER
    assert stats.tenacity is None
    assert stats.build is None


def test_job_stats_model_serializes_role_as_a_string():
    stats = JobStatsModel.model_validate(job_stats_data())

    assert stats.model_dump(mode="json")["role"] == "Healer"


def test_tank_requires_tenacity():
    with pytest.raises(ValidationError, match="Tenacity is required"):
        JobStatsModel.model_validate(job_stats_data(role=Role.TANK))


def test_non_tank_rejects_tenacity():
    with pytest.raises(ValidationError, match="Tenacity is only valid"):
        JobStatsModel.model_validate(job_stats_data(tenacity=1000))


def test_tank_accepts_tenacity_in_range():
    stats = JobStatsModel.model_validate(job_stats_data(role=Role.TANK, tenacity=1000))

    assert stats.tenacity == 1000


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("main_stat", 3199),
        ("determination", 5001),
        ("speed_stat", 379),
        ("critical_hit", 5001),
        ("direct_hit", 379),
        ("weapon_damage", 251),
    ],
)
def test_job_stats_model_enforces_stat_ranges(field, invalid_value):
    with pytest.raises(ValidationError):
        JobStatsModel.model_validate(job_stats_data(**{field: invalid_value}))


def test_etro_build_rejects_an_xivgear_selection_index():
    with pytest.raises(ValidationError, match="build_index is only valid"):
        BuildModel(
            build_provider=BuildProvider.ETRO,
            build_id="etro-build-id",
            build_index=0,
        )


def test_xivgear_build_accepts_an_optional_selection_index():
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
    assert set(ROLE_SPECS) == set(Role)
    assert ROLE_SPECS[Role.TANK].requires_tenacity
    assert ROLE_SPECS[Role.HEALER].speed_stat_placeholder == "Spell Speed"
