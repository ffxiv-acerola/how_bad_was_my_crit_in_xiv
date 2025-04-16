import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.reaper import ReaperActions

reaper_id_map = {
    "Cross Reaping": 24396,
    "Gallows": 24383,
    "Gibbet": 24382,
    "Void Reaping": 24395,
    "Plentiful Harvest": 24385,
    "Enhanced Cross Reaping": 1002591,
    "Enhanced Gallows": 1002589,
    "Enhanced Gibbet": 1002588,
    "Enhanced Void Reaping": 1002590,
    "Immortal Sacrifice": 1002592,
    "Executioners Gibbet": 0,
    "Executioners Gallows": 0,
}


@pytest.fixture
def mock_reaper(monkeypatch):
    """Mock buff times function for ReaperActions.

    This fixture patches the set_enhanced_times method to return empty buff windows,
    eliminating API dependencies during testing.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """

    def mock_enhanced_times(*args, **kwargs):
        # Return empty arrays for all buff windows
        empty_array = np.array([[-1, -1]])
        empty_immortal = np.array([[-1, -1, -1]])  # [start, end, stacks]
        return empty_array, empty_array, empty_array, empty_array, empty_immortal

    monkeypatch.setattr(ReaperActions, "set_enhanced_times", mock_enhanced_times)


@pytest.mark.parametrize(
    "timestamp, ability_id, enhanced_times, expected_buffs",
    [
        # Cross Reaping with Enhanced buff
        (
            1500,
            reaper_id_map["Cross Reaping"],
            [[1000, 2000]],
            [str(reaper_id_map["Enhanced Cross Reaping"])],
        ),
        # Gallows with Enhanced buff
        (
            1500,
            reaper_id_map["Gallows"],
            [[1000, 2000]],
            [
                str(reaper_id_map["Enhanced Gallows"]),
                str(reaper_id_map["Executioners Gallows"]),
            ],
        ),
        # Gibbet with Enhanced buff
        (
            1500,
            reaper_id_map["Gibbet"],
            [[1000, 2000]],
            [
                str(reaper_id_map["Enhanced Gibbet"]),
                str(reaper_id_map["Executioners Gibbet"]),
            ],
        ),
        # Void Reaping with Enhanced buff
        (
            1500,
            reaper_id_map["Void Reaping"],
            [[1000, 2000]],
            [str(reaper_id_map["Enhanced Void Reaping"])],
        ),
        # Ability outside any buff window
        (2500, reaper_id_map["Cross Reaping"], [[1000, 2000]], []),
    ],
)
def test_apply_enhanced_buffs(timestamp, ability_id, enhanced_times, expected_buffs, monkeypatch, mock_reaper):
    """Test that enhanced buffs are correctly applied to actions."""
    reaper = ReaperActions({}, "dummy", 1, 1)

    # Set the specific enhanced buff times based on the test case
    if ability_id == reaper_id_map["Cross Reaping"]:
        reaper.enhanced_cross_reaping_times = np.array(enhanced_times)
    elif ability_id == reaper_id_map["Gallows"]:
        reaper.enhanced_gallows_times = np.array(enhanced_times)
    elif ability_id == reaper_id_map["Gibbet"]:
        reaper.enhanced_gibbet_times = np.array(enhanced_times)
    elif ability_id == reaper_id_map["Void Reaping"]:
        reaper.enhanced_void_reaping_times = np.array(enhanced_times)

    # Create a dummy DataFrame with one row event
    df = pd.DataFrame(
        {
            "timestamp": [timestamp],
            "abilityGameID": [ability_id],
            "buffs": [[]],
            "action_name": ["dummy-action"],
            "ability_name": ["dummy-action"],
            "multiplier": [1.0],
            "index": [0],
            "elapsed_time": [timestamp],
        }
    )
    df.set_index("index", inplace=True)

    result = reaper.apply_enhanced_buffs(df)
    assert set(result.loc[0, "buffs"]) == set(expected_buffs)


@pytest.mark.parametrize(
    "stack_count, timestamp",
    [
        (6, 1500),
        (7, 2500),
        (8, 3500),
    ],
)
def test_immortal_sacrifice_stacks(stack_count, timestamp, monkeypatch, mock_reaper):
    """Test that Plentiful Harvest gets the correct Immortal Sacrifice buff based on stacks."""
    reaper = ReaperActions({}, "dummy", 1, 1)

    # Set up an immortal sacrifice window with the specified stack count
    immortal_window = np.array([[1000, 2000, stack_count]])
    if stack_count == 7:
        immortal_window = np.array([[2000, 3000, stack_count]])
    elif stack_count == 8:
        immortal_window = np.array([[3000, 4000, stack_count]])

    reaper.immortal_sacrifice_times = immortal_window

    # Create a dummy DataFrame with Plentiful Harvest
    df = pd.DataFrame(
        {
            "timestamp": [timestamp],
            "abilityGameID": [reaper_id_map["Plentiful Harvest"]],
            "buffs": [[]],
            "action_name": ["Plentiful Harvest"],
            "ability_name": ["Plentiful Harvest"],
            "multiplier": [1.0],
            "index": [0],
            "elapsed_time": [timestamp],
        }
    )
    df.set_index("index", inplace=True)

    result = reaper.apply_enhanced_buffs(df)
    expected_buff = f"immortal_sac_{stack_count}"

    assert expected_buff in result.loc[0, "buffs"], f"Expected {expected_buff} to be applied"


def test_immortal_sacrifice_out_of_window(monkeypatch, mock_reaper):
    """Test that Plentiful Harvest outside of Immortal Sacrifice window gets no buff."""
    reaper = ReaperActions({}, "dummy", 1, 1)

    # Set up immortal sacrifice windows for each stack count
    reaper.immortal_sacrifice_times = np.array(
        [
            [1000, 2000, 6],
            [2000, 3000, 7],
            [3000, 4000, 8],
        ]
    )

    # Create a dummy DataFrame with Plentiful Harvest outside of any window
    df = pd.DataFrame(
        {
            "timestamp": [5000],
            "abilityGameID": [reaper_id_map["Plentiful Harvest"]],
            "buffs": [[]],
            "action_name": ["Plentiful Harvest"],
            "ability_name": ["Plentiful Harvest"],
            "multiplier": [1.0],
            "index": [0],
            "elapsed_time": [5000],
        }
    )
    df.set_index("index", inplace=True)

    result = reaper.apply_enhanced_buffs(df)

    # Verify no immortal_sac buffs were applied
    immortal_buffs = [buff for buff in result.loc[0, "buffs"] if "immortal_sac" in buff]
    assert len(immortal_buffs) == 0, "No immortal sacrifice buffs should be applied outside window"


def test_multiple_abilities_with_different_buffs(monkeypatch, mock_reaper):
    """Test multiple abilities with different buff conditions."""
    reaper = ReaperActions({}, "dummy", 1, 1)

    # Set up different buff windows
    reaper.enhanced_gibbet_times = np.array([[1000, 2000]])
    reaper.enhanced_gallows_times = np.array([[2000, 3000]])
    reaper.immortal_sacrifice_times = np.array(
        [
            [3000, 4000, 6],
            [4000, 5000, 7],
            [5000, 6000, 8],
        ]
    )

    # Create a DataFrame with multiple abilities
    df = pd.DataFrame(
        {
            "timestamp": [1500, 2500, 3500, 4500, 5500],
            "abilityGameID": [
                reaper_id_map["Gibbet"],
                reaper_id_map["Gallows"],
                reaper_id_map["Plentiful Harvest"],
                reaper_id_map["Plentiful Harvest"],
                reaper_id_map["Plentiful Harvest"],
            ],
            "buffs": [[], [], [], [], []],
            "action_name": [
                "Gibbet",
                "Gallows",
                "Plentiful Harvest",
                "Plentiful Harvest",
                "Plentiful Harvest",
            ],
            "ability_name": [
                "Gibbet",
                "Gallows",
                "Plentiful Harvest",
                "Plentiful Harvest",
                "Plentiful Harvest",
            ],
            "multiplier": [1.0, 1.0, 1.0, 1.0, 1.0],
            "index": [0, 1, 2, 3, 4],
            "elapsed_time": [1500, 2500, 3500, 4500, 5500],
        }
    )
    df.set_index("index", inplace=True)

    result = reaper.apply_enhanced_buffs(df)

    # Check each ability has the correct buffs
    assert str(reaper_id_map["Enhanced Gibbet"]) in result.loc[0, "buffs"]
    assert str(reaper_id_map["Executioners Gibbet"]) in result.loc[0, "buffs"]

    assert str(reaper_id_map["Enhanced Gallows"]) in result.loc[1, "buffs"]
    assert str(reaper_id_map["Executioners Gallows"]) in result.loc[1, "buffs"]

    assert "immortal_sac_6" in result.loc[2, "buffs"]
    assert "immortal_sac_7" in result.loc[3, "buffs"]
    assert "immortal_sac_8" in result.loc[4, "buffs"]


@pytest.mark.parametrize(
    "mock_response_data, expected_result",
    [
        # Basic test with two buff windows (6 and 7 stacks)
        (
            [
                {"timestamp": 1000, "type": "applybuff", "stack": 6},
                {"timestamp": 2000, "type": "removebuff", "stack": 6},
                {"timestamp": 3000, "type": "applybuff", "stack": 7},
                {"timestamp": 4000, "type": "removebuff", "stack": 7},
            ],
            [
                [1000, 2000, 6],  # First buff window with 6 stacks
                [3000, 4000, 7],  # Second buff window with 7 stacks
            ],
        ),
        # Single buff test with 8 stacks
        (
            [
                {"timestamp": 5000, "type": "applybuff", "stack": 8},
                {"timestamp": 8000, "type": "removebuff", "stack": 8},
            ],
            [[5000, 8000, 8]],  # Single window with 8 stacks
        ),
        # Multiple stacks test
        (
            [
                {"timestamp": 1000, "type": "applybuff", "stack": 6},
                {"timestamp": 2000, "type": "removebuff", "stack": 6},
                {"timestamp": 3000, "type": "applybuff", "stack": 7},
                {"timestamp": 4000, "type": "removebuff", "stack": 7},
                {"timestamp": 5000, "type": "applybuff", "stack": 8},
                {"timestamp": 6000, "type": "removebuff", "stack": 8},
                {"timestamp": 7000, "type": "applybuff", "stack": 6},
                {"timestamp": 8000, "type": "removebuff", "stack": 6},
            ],
            [
                [1000, 2000, 6],  # First window with 6 stacks
                [3000, 4000, 7],  # Window with 7 stacks
                [5000, 6000, 8],  # Window with 8 stacks
                [7000, 8000, 6],  # Second window with 6 stacks
            ],
        ),
        # Empty response test
        (
            [],
            [[0, 0]],  # Empty result
        ),
    ],
)
def test_immortal_sacrifice_counter(mock_response_data, expected_result, monkeypatch, mock_reaper):
    """Test the immortal sacrifice counter with parameterized test cases."""
    reaper = ReaperActions({}, "dummy", 1, 1)
    reaper.report_start = 0

    # Create a mock response with the specified data
    mock_response = {"data": {"reportData": {"report": {"immortalSacrifice": {"data": mock_response_data}}}}}

    result = reaper._immortal_sacrifice_counter(mock_response)

    # For non-empty results, check the values
    expected_array = np.array(expected_result)
    assert result.shape == expected_array.shape
    assert result.tolist() == expected_array.tolist()
