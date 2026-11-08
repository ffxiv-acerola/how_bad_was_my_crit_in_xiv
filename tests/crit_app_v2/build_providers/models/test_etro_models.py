"""Tests for typed Etro API response models."""

from typing import Any

import pytest
from pydantic import ValidationError

from crit_app_v2.build_providers.models import EtroBuildResponse


def etro_response(job_abbrev: str, stats: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal Etro response from named stat values."""
    return {
        "name": "Test build",
        "jobAbbrev": job_abbrev,
        "partyBonus": 1.05,
        "totalParams": [{"name": name, "value": value} for name, value in stats.items()],
    }


def test_etro_response_validates_required_tank_stats_and_ignores_extras():
    """Accept required Tank stats while ignoring unrelated API data."""
    response_data = etro_response(
        "PLD",
        {
            "STR": 6772,
            "DET": 3066,
            "SKS": 420,
            "CRT": 3595,
            "DH": 1230,
            "Weapon Damage": 158,
            "TEN": 622,
            "Food Values": {"DET": 151},
            "Medicine Values": None,
            "Future unrelated parameter": None,
        },
    )
    response_data["unneededResponseField"] = {"arbitrary": "data"}
    response_data["totalParams"].append({"name": "Future entry without a value"})

    response = EtroBuildResponse.model_validate(response_data)

    assert response.job.value == "Paladin"
    assert response.required_stats == {
        "STR": 6772,
        "DET": 3066,
        "SKS": 420,
        "CRT": 3595,
        "DH": 1230,
        "Weapon Damage": 158,
        "TEN": 622,
    }


def test_etro_response_requires_job_specific_main_and_speed_stats():
    """Require MND and SPS for a healer rather than other valid stat names."""
    data = etro_response(
        "WHM",
        {
            "STR": 6000,
            "SKS": 420,
            "DET": 3066,
            "CRT": 3595,
            "DH": 1230,
            "Weapon Damage": 158,
        },
    )

    with pytest.raises(ValidationError, match="MND.*SPS"):
        EtroBuildResponse.model_validate(data)


def test_etro_response_rejects_duplicate_required_stats():
    """Reject ambiguous values for any stat consumed by the loader."""
    data = etro_response(
        "WHM",
        {
            "MND": 6000,
            "DET": 3066,
            "SPS": 420,
            "CRT": 3595,
            "DH": 1230,
            "Weapon Damage": 158,
        },
    )
    data["totalParams"].append({"name": "DET", "value": 3067})

    with pytest.raises(ValidationError, match="duplicate required stats"):
        EtroBuildResponse.model_validate(data)


def test_etro_response_requires_integer_values_for_required_stats():
    """Reject non-integer values for stats used to create the loaded build."""
    data = etro_response(
        "WHM",
        {
            "MND": 6000,
            "DET": 3066.5,
            "SPS": 420,
            "CRT": 3595,
            "DH": 1230,
            "Weapon Damage": 158,
        },
    )

    with pytest.raises(ValidationError, match="must be integers"):
        EtroBuildResponse.model_validate(data)
