"""Tests for strict role-build ranges and Tenacity invariants."""

import pytest
from pydantic import ValidationError

from crit_app_v2.build_providers.models import RoleBuildStatsModel, ValidatedRoleBuild
from crit_app_v2.game_data import STAT_INPUTS, Role, Stats


def _stat_values() -> dict[str, int | None]:
    """Return Tank stat values at canonical lower bounds."""
    return {
        "main_stat": STAT_INPUTS[Stats.MAIN_STAT].lower,
        "determination": STAT_INPUTS[Stats.DETERMINATION].lower,
        "speed_stat": STAT_INPUTS[Stats.SPEED_STAT].lower,
        "critical_hit": STAT_INPUTS[Stats.CRITICAL_HIT].lower,
        "direct_hit": STAT_INPUTS[Stats.DIRECT_HIT].lower,
        "weapon_damage": STAT_INPUTS[Stats.WEAPON_DAMAGE].lower,
        "tenacity": STAT_INPUTS[Stats.TENACITY].lower,
    }


@pytest.mark.parametrize("stat", list(Stats), ids=[stat.value for stat in Stats])
@pytest.mark.parametrize("boundary", ["lower", "upper"], ids=["minimum", "maximum"])
def test_validated_tank_build_accepts_canonical_boundaries(stat: Stats, boundary: str) -> None:
    """Accept inclusive stat boundaries from canonical STAT_INPUTS."""
    field_name = {
        Stats.MAIN_STAT: "main_stat",
        Stats.DETERMINATION: "determination",
        Stats.SPEED_STAT: "speed_stat",
        Stats.CRITICAL_HIT: "critical_hit",
        Stats.DIRECT_HIT: "direct_hit",
        Stats.WEAPON_DAMAGE: "weapon_damage",
        Stats.TENACITY: "tenacity",
    }[stat]
    limits = STAT_INPUTS[stat]
    values = _stat_values()
    values[field_name] = limits.lower if boundary == "lower" else limits.upper

    ValidatedRoleBuild(
        role=Role.TANK,
        stats=RoleBuildStatsModel(**values),
    )


@pytest.mark.parametrize("stat", list(Stats), ids=[stat.value for stat in Stats])
def test_validated_tank_build_rejects_stat_above_canonical_maximum(
    stat: Stats,
) -> None:
    """Reject values above each stat's canonical upper limit."""
    field_name = {
        Stats.MAIN_STAT: "main_stat",
        Stats.DETERMINATION: "determination",
        Stats.SPEED_STAT: "speed_stat",
        Stats.CRITICAL_HIT: "critical_hit",
        Stats.DIRECT_HIT: "direct_hit",
        Stats.WEAPON_DAMAGE: "weapon_damage",
        Stats.TENACITY: "tenacity",
    }[stat]
    values = _stat_values()
    values[field_name] = STAT_INPUTS[stat].upper + 1

    with pytest.raises(ValidationError, match=f"{stat.value} must be between"):
        ValidatedRoleBuild(
            role=Role.TANK,
            stats=RoleBuildStatsModel(**values),
        )


def test_validated_non_tank_build_requires_tenacity_to_be_omitted() -> None:
    """Accept a non-Tank build when its hidden Tenacity value is absent."""
    values = _stat_values()
    values["tenacity"] = None

    build = ValidatedRoleBuild(
        role=Role.HEALER,
        stats=RoleBuildStatsModel(**values),
    )

    assert build.stats.tenacity is None


def test_validated_non_tank_build_rejects_tenacity() -> None:
    """Reject stale Tenacity values on a non-Tank build."""
    with pytest.raises(ValidationError, match="Non-Tanks must not provide Tenacity"):
        ValidatedRoleBuild(
            role=Role.HEALER,
            stats=RoleBuildStatsModel(**_stat_values()),
        )


def test_validated_tank_build_requires_tenacity() -> None:
    """Require a Tenacity value for Tank builds."""
    values = _stat_values()
    values["tenacity"] = None

    with pytest.raises(ValidationError, match="Tanks require a Tenacity value"):
        ValidatedRoleBuild(
            role=Role.TANK,
            stats=RoleBuildStatsModel(**values),
        )
