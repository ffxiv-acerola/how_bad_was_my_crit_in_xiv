"""Pickle persistence for player-analysis rotations and distributions."""

import os
import pickle
import tempfile
from pathlib import Path

from crit_app_v2.analysis.dps_distribution import PlayerDpsDistribution
from crit_app_v2.config import BLOB_URI


def save_player_analysis_blobs(
    analysis_id: str,
    rotation: object,
    distribution: PlayerDpsDistribution,
    blob_uri: Path = BLOB_URI,
) -> None:
    """Atomically persist rotation and compact distribution pickle files.

    Parameters
    ----------
    analysis_id
        Identifier used to name both blob files.
    rotation
        Rotation-table object required by the result visualization.
    distribution
        Validated, reduced DPS distribution model.
    blob_uri
        Directory where application analysis blobs are stored.

    Raises
    ------
    OSError
        If the destination cannot be created or written.
    pickle.PickleError
        If either object cannot be serialized.
    """
    blob_uri.mkdir(parents=True, exist_ok=True)
    _write_pickle(blob_uri / f"rotation-object-{analysis_id}.pkl", rotation)
    _write_pickle(blob_uri / f"job-analysis-data-{analysis_id}.pkl", distribution)


def _write_pickle(path: Path, value: object) -> None:
    """Write one pickle to a temporary file before replacing its destination."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary_path = Path(file.name)
            pickle.dump(value, file, protocol=pickle.HIGHEST_PROTOCOL)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
