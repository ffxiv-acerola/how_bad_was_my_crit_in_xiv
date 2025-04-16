"""BLM tests after 7.2 rework."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.black_mage import BlackMageActions


# Create a dummy subclass to bypass remote data fetching.
class DummyBlackMageActions(BlackMageActions):
    def _get_elemental_gauge_actions(self, headers, actions_df=None) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                "timestamp": [0, 2000, 3000],
                "elapsed_time": [0, 1, 2],
                "ability_name": ["Fire", "Paradox", "Transpose"],
                "previous_action": [None, "Fire", "Paradox"],
                "previous_time": [np.nan, 0, 1],
            }
        )
        self.elemental_gauge_df = df
        return df

    def _set_elemental_timings(self):
        """
        For testing only: replicate final steps from your constructor.

        to populate elemental_state, elemental_state_changes, etc.
        """
        self.elemental_state = self._get_elemental_state_df(self.elemental_gauge_df)
        self.elemental_state_changes = self._get_elemental_state_changes(self.elemental_state)
        self.elemental_state_times = self._get_elemental_state_timings(self.elemental_state_changes)
        self.enochian_times = self._enochian_times(self.elemental_state_changes)


@pytest.fixture
def bm():
    bm_instance = DummyBlackMageActions(
        actions_df=pd.DataFrame(),
        headers={},
        report_id="dummy",
        fight_id=1,
        player_id=1,
        level=100,
        phase=1,
        patch_number=7.2,
    )
    # Re-initialize data and call the testing method.
    bm_instance._get_elemental_gauge_actions({})
    return bm_instance


# --------------------------------------------------------------------
@pytest.mark.parametrize(
    "action,time_delta",
    [
        ("Umbral Soul", 0.3),
        ("Fire", 1.0),
        ("Despair", 0.0),
        ("Flare", 2.0),
        ("Blizzard III", 0.5),
        ("Blizzard", 1.5),
        ("High Blizzard II", 2.0),
        ("Paradox", 0.2),
        ("Transpose", 0.1),
        ("Manafont", 5.0),
    ],
)
def test_elemental_time_remaining(bm, action, time_delta):
    """
    Test _elemental_time_remaining using parameterization.

    For a given action, the expected time remaining is:
    - For "Umbral Soul": always 1000.
    - For any other granting action: max(0, granting_time - time_delta)
    All granting actions have a "time" value of 15 per your config.
    """
    all_actions = bm.fire_granting_actions | bm.ice_granting_actions | bm.other_granting_actions
    expected_duration = all_actions[action]["time"] - time_delta
    # _elemental_time_remaining expects an action that is either "Umbral Soul"
    # or found in the merge of fire_granting_actions, ice_granting_actions, or other_granting_actions.
    result = bm._elemental_time_remaining(action, time_delta)
    assert result == expected_duration


# --------------------------------------------------------------------
# Test _elemental_status_granted.
# For fire actions, status should be "Astral Fire".
# For ice actions, status should be "Umbral Ice".
# For "Paradox", it returns the provided active status.
# For "Transpose", it swaps "Astral Fire" and "Umbral Ice" (or returns None if no state).
@pytest.mark.parametrize(
    "action,active_input,expected",
    [
        ("Fire", None, "Astral Fire"),
        ("Despair", "Umbral Ice", "Astral Fire"),
        ("Blizzard III", None, "Umbral Ice"),
        ("Blizzard", "Astral Fire", "Umbral Ice"),
        ("Paradox", "Astral Fire", "Astral Fire"),
        ("Paradox", "Umbral Ice", "Umbral Ice"),
        ("Transpose", "Astral Fire", "Umbral Ice"),
        ("Transpose", "Umbral Ice", "Astral Fire"),
        ("Transpose", None, None),
    ],
)
def test_elemental_status_granted(bm, action, active_input, expected):
    result = bm._elemental_status_granted(action, active_input)
    assert result == expected


# --------------------------------------------------------------------
# Test _elemental_time_granted.
# Simply verifies that for any granting action the configured time is returned.
@pytest.mark.parametrize(
    "action",
    [
        "Fire",
        "Despair",
        "Flare",
        "Blizzard III",
        "Blizzard",
        "High Blizzard II",
        "Paradox",
        "Transpose",
        "Manafont",
        "Umbral Soul",
    ],
)
def test_elemental_time_granted(bm, action):
    expected = 500
    result = bm._elemental_time_granted(action)
    assert result == expected


# --------------------------------------------------------------------
# Test _elemental_stacks_granted.
@pytest.mark.parametrize(
    "action,current_stacks,active_state,expected",
    [
        ("Transpose", 0, None, 0),
        ("Transpose", 0, "Astral Fire", 1),
        ("Paradox", 1, "Astral Fire", 1),
        ("Paradox", 1, "Umbral Ice", 1),
        ("Paradox", 3, "Umbral Ice", 3),  # Already at cap
        ("Umbral Soul", 1, "Umbral Ice", 2),
        ("Umbral Soul", 3, "Umbral Ice", 3),
        ("Manafont", 1, "Astral Fire", 3),
        ("Fire", 0, None, 1),  # fire_granting_actions["Fire"]["stacks"] is 1
        ("Flare", 0, None, 3),  # flare has 3 stacks
        ("Blizzard", 0, None, 1),  # ice granting
        ("Blizzard III", 0, None, 3),
    ],
)
def test_elemental_stacks_granted(bm, action, current_stacks, active_state, expected):
    result = bm._elemental_stacks_granted(action, current_stacks, active_state)
    assert result == expected


# --------------------------------------------------------------------
@pytest.mark.parametrize(
    "input_file,expected_file",
    [
        ("blm_elemental_state_7_2.csv", "blm_elemental_state_changes_7_2.csv"),
    ],
)
def test_get_elemental_state_changes_csv(bm, input_file, expected_file):
    """
    Test elemental states are correctly transformed to elemental state changes.

    Two test cases are parameterized:
    1. Changes I cooked up, ensures that AF/UI doesn't fall off, paradox doesn't affect
    UI or AF stacks, usual BLM gauge things, including overcap effects.
    """
    base_dir = Path(__file__).parent / "unit_test_data" / "blm"
    input_csv = base_dir / input_file
    expected_csv = base_dir / expected_file

    # Read input CSV and process DataFrame.
    state_df = pd.read_csv(input_csv).replace({np.nan: None})
    changes_df = bm._get_elemental_state_changes(state_df)

    # Read expected output CSV.
    expected_df = pd.read_csv(expected_csv).replace({np.nan: None})

    # Reset indices to ignore index differences.
    changes_df = changes_df.reset_index(drop=True)
    expected_df = expected_df.reset_index(drop=True)

    # Verify that the DataFrames match.
    pd.testing.assert_frame_equal(changes_df, expected_df)


# TODO: test changes
# @pytest.mark.parametrize(
#     "input_file,expected_file",
#     [
#         (
#             "blm_apply_buffs_input_2.parquet",
#             "blm_apply_buffs_expected_output_2.parquet",
#         ),
#     ],
# )
# def test_apply_blm_buffs(bm, input_file, expected_file):
#     """
#     Test apply_blm_buffs using external parquet test data.

#     Only the following columns are compared:
#         - "action_name"
#         - "multiplier"
#         - "elemental_type"
#         - "elemental_state"
#         - "enochian_multiplier"
#         - "elemental_multiplier"
#     """
#     assert True
