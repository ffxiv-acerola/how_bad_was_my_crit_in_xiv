"""Tests for persisted player-analysis blob files."""

import pickle
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from crit_app_v2.analysis.dps_distribution import PlayerDpsDistribution
from crit_app_v2.db.analysis_blobs import save_player_analysis_blobs


def test_blob_writer_saves_rotation_and_reduced_distribution(
    tmp_path: Path,
) -> None:
    """Write both named pickle blobs and preserve the typed distribution."""
    rotation = SimpleNamespace(rotation_df="test rotation")
    distribution = PlayerDpsDistribution(
        active_dps_t=90.0,
        analysis_t=100.0,
        rotation_mean=1500.0,
        rotation_variance=20.0,
        rotation_std=4.5,
        rotation_skewness=0.1,
        rotation_dps_distribution=np.array([0.1, 0.2, 0.1]),
        rotation_dps_support=np.array([1000.0, 1500.0, 2000.0]),
        unique_actions_distribution={},
    )

    save_player_analysis_blobs("analysis-id", rotation, distribution, tmp_path)

    loaded_rotation = pickle.loads((tmp_path / "rotation-object-analysis-id.pkl").read_bytes())
    loaded_distribution = pickle.loads((tmp_path / "job-analysis-data-analysis-id.pkl").read_bytes())
    assert loaded_rotation.rotation_df == "test rotation"
    assert isinstance(loaded_distribution, PlayerDpsDistribution)
    assert np.array_equal(loaded_distribution.rotation_dps_support, distribution.rotation_dps_support)
