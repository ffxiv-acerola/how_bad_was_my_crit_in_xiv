"""Tests for validated, compact player DPS distribution data."""

import pickle
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from crit_app_v2.analysis.dps_distribution import (
    ActionDistribution,
    PlayerDpsDistribution,
)


def _job_result(size: int = 6001) -> SimpleNamespace:
    """Build a lightweight rotation result with large sampled arrays."""
    support = np.linspace(1000, 2000, size)
    density = np.linspace(0.1, 0.2, size)
    return SimpleNamespace(
        t=120.0,
        rotation_mean=1500.0,
        rotation_variance=20.0,
        rotation_std=4.5,
        rotation_skewness=0.1,
        rotation_dps_distribution=density,
        rotation_dps_support=support,
        unique_actions_distribution={
            "Test Action": {
                "support": support,
                "dps_distribution": density,
            }
        },
    )


def test_factory_stores_only_reduced_distribution_arrays() -> None:
    """Reduce raw rotation and action arrays before retaining the model."""
    result = PlayerDpsDistribution.from_job_analysis(_job_result(), 115.0)

    assert result.rotation_dps_distribution.shape == (5000,)
    assert result.rotation_dps_support.shape == (5000,)
    action = result.unique_actions_distribution["Test Action"]
    assert isinstance(action, ActionDistribution)
    assert action.support.shape == (5000,)
    assert action.dps_distribution.shape == (5000,)
    assert result.rotation_dps_support[[0, -1]].tolist() == [1000.0, 2000.0]


@pytest.mark.parametrize(
    "field,value",
    [
        ("rotation_dps_distribution", np.array([0.1, np.nan, 0.2])),
        ("rotation_dps_support", np.array([1.0, np.inf, 3.0])),
    ],
    ids=["rotation-pdf-nan", "rotation-support-infinite"],
)
def test_rotation_arrays_reject_non_finite_values(field: str, value: np.ndarray) -> None:
    """Reject NaN and infinite values in rotation distribution arrays."""
    job = _job_result(size=3)
    setattr(job, field, value)

    with pytest.raises(ValidationError, match="finite"):
        PlayerDpsDistribution.from_job_analysis(job, 100.0)


def test_action_distribution_rejects_nan_values() -> None:
    """Reject NaN values in an individual action's PDF."""
    with pytest.raises(ValidationError, match="finite"):
        ActionDistribution(
            support=np.array([1.0, 2.0, 3.0]),
            dps_distribution=np.array([0.1, np.nan, 0.2]),
        )


def test_distribution_rejects_mismatched_array_lengths() -> None:
    """Require matching rotation density and support array lengths."""
    job = _job_result(size=3)
    job.rotation_dps_distribution = np.array([0.1, 0.2])

    with pytest.raises(ValidationError, match="equal lengths"):
        PlayerDpsDistribution.from_job_analysis(job, 100.0)


def test_model_pickle_round_trip_preserves_reduced_fields() -> None:
    """Pickle compact distributions while retaining all named fields."""
    model = PlayerDpsDistribution.from_job_analysis(_job_result(), 115.0)

    loaded = pickle.loads(pickle.dumps(model))

    assert loaded.model_dump().keys() == model.model_dump().keys()
    assert np.array_equal(loaded.rotation_dps_distribution, model.rotation_dps_distribution)
    assert loaded.unique_actions_distribution["Test Action"].support.shape == (5000,)
