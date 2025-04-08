import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.samurai import SamuraiActions


@pytest.fixture
def mock_samurai(monkeypatch):
    def mock_enpi_times(*args, **kwargs):
        return np.array([[-1, -1]]), np.array([[-1, -1]])

    monkeypatch.setattr(SamuraiActions, "get_enhanced_enpi_times", mock_enpi_times)
    # Return a dummy SamuraiActions instance with default parameters.


# Parameterized tests for apply_enhanced_enpi
@pytest.mark.parametrize(
    "timestamp, abilityGameID, windows, expected",
    [
        # Case: no buff windows; should return no buff applied.
        (1500, 7486, np.array([[-1, -1]]), []),
        # Case: matching ability within window -> buff applied.
        (1500, 7486, np.array([[1000, 2000]]), [str(1001236)]),
        # Case: matching ability but outside window -> no buff.
        (2500, 7486, np.array([[1000, 2000]]), []),
        # Case: non-matching ability within window -> no buff.
        (1500, 1234, np.array([[1000, 2000]]), []),
        # Edge: timestamp equal to window start (left-exclusive) -> no buff.
        (1000, 7486, np.array([[1000, 2000]]), []),
        # Edge: timestamp equal to window end (right-inclusive) -> buff applied.
        (2000, 7486, np.array([[1000, 2000]]), [str(1001236)]),
    ],
)
def test_apply_enhanced_enpi(
    timestamp, abilityGameID, windows, expected, monkeypatch, mock_samurai
):
    sam = SamuraiActions({}, "dummy", 1, 1)
    # Override enhanced_enpi_times with provided window(s)
    sam.enhanced_enpi_times = windows

    # Create a dummy DataFrame mimicking an action row.
    df = pd.DataFrame(
        {
            "timestamp": [timestamp],
            "abilityGameID": [abilityGameID],
            "buffs": [[]],
            "action_name": ["dummy-action"],
        }
    )

    result = sam.apply_enhanced_enpi(df)
    assert result.loc[0, "buffs"] == expected
