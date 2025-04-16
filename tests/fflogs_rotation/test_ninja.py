import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.ninja import NinjaActions

nin_id_map = {
    "Bhavacakra": 7402,
    "Zesho Meppo": 36960,
    "Ninjutsu": 2265,
    "Aeolian Edge": 2255,
    "Armor Crush": 3563,
    "Meisui": 1002689,
    "Kassatsu": 1000497,
}


@pytest.fixture
def mock_nin(monkeypatch):
    """Mock buff times function for NinjaActions.

    This fixture patches the set_nin_buff_times method to return empty buff windows,
    eliminating API dependencies during testing.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """

    def mock_nin_buff_times(*args, **kwargs):
        return np.array([[-1, -1]]), np.array([[-1, -1]])

    monkeypatch.setattr(NinjaActions, "set_nin_buff_times", mock_nin_buff_times)


@pytest.mark.parametrize(
    "timestamp, ability_id, meisui_times, kassatsu_times, expected_buffs",
    [
        # Bhavacakra in Meisui window -> Meisui buff applied
        (
            1500,
            nin_id_map["Bhavacakra"],
            [[1000, 2000]],
            [[-1, -1]],
            [str(nin_id_map["Meisui"])],
        ),
        # Zesho Meppo in Meisui window -> Meisui buff applied
        (
            1500,
            nin_id_map["Zesho Meppo"],
            [[1000, 2000]],
            [[-1, -1]],
            [str(nin_id_map["Meisui"])],
        ),
        # Ninjutsu in Kassatsu window -> Kassatsu buff applied
        (
            3500,
            nin_id_map["Ninjutsu"],
            [[-1, -1]],
            [[3000, 4000]],
            [str(nin_id_map["Kassatsu"])],
        ),
        # Bhavacakra outside any buff windows -> No buff applied
        (2500, nin_id_map["Bhavacakra"], [[1000, 2000]], [[3000, 4000]], []),
        # Ninjutsu outside any buff windows -> No buff applied
        (2500, nin_id_map["Ninjutsu"], [[1000, 2000]], [[3000, 4000]], []),
    ],
)
def test_apply_ninja_buffs(
    timestamp,
    ability_id,
    meisui_times,
    kassatsu_times,
    expected_buffs,
    monkeypatch,
    mock_nin,
):
    nin = NinjaActions({}, "dummy", 1, 1, 7.0)
    nin.meisui_times = np.array(meisui_times)
    nin.kassatsu_times = np.array(kassatsu_times)

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

    result = nin.apply_ninja_buff(df)
    assert result.loc[0, "buffs"] == expected_buffs


@pytest.mark.parametrize(
    "ability_sequence, expected_stacks",
    [
        # Start at 0, add Armor Crush (+2), goes to 2
        ([(nin_id_map["Armor Crush"], "Armor Crush")], [0]),
        # Start at 0, Armor Crush (+2), Armor Crush (+2) -> 4
        (
            [
                (nin_id_map["Armor Crush"], "Armor Crush"),
                (nin_id_map["Armor Crush"], "Armor Crush"),
            ],
            [0, 2],
        ),
        # Start at 0, Armor Crush (+2), Aeolian Edge (-1) -> 1
        (
            [
                (nin_id_map["Armor Crush"], "Armor Crush"),
                (nin_id_map["Aeolian Edge"], "Aeolian Edge"),
            ],
            [0, 2],
        ),
        # Max out at 5: 0 -> 2 -> 4 -> 5 (capped)
        (
            [
                (nin_id_map["Armor Crush"], "Armor Crush"),
                (nin_id_map["Armor Crush"], "Armor Crush"),
                (nin_id_map["Armor Crush"], "Armor Crush"),
            ],
            [0, 2, 4],
        ),
        # Prevent underflow: 0 -> 2 -> 1 -> 0 -> 0 (can't go below 0)
        (
            [
                (nin_id_map["Armor Crush"], "Armor Crush"),
                (nin_id_map["Aeolian Edge"], "Aeolian Edge"),
                (nin_id_map["Aeolian Edge"], "Aeolian Edge"),
                (nin_id_map["Aeolian Edge"], "Aeolian Edge"),
            ],
            [0, 2, 1, 0],
        ),
    ],
)
def test_track_kazematoi_gauge(ability_sequence, expected_stacks, mock_nin):
    # Instantiate NinjaActions with dummy parameters
    nin = NinjaActions({}, "dummy", 1, 1, 7.0)

    # Create DataFrame with ability sequence
    data = {
        "elapsed_time": list(range(len(ability_sequence))),
        "abilityGameID": [ability[0] for ability in ability_sequence],
        "ability_name": [ability[1] for ability in ability_sequence],
        "index": list(range(len(ability_sequence))),
    }

    df = pd.DataFrame(data)
    df.set_index("index", inplace=True)

    result = nin._track_kazematoi_gauge(df)

    # Clearer assertion with better error messages
    assert (
        list(result["initial_stacks"]) == expected_stacks
    ), f"Gauge stacks {list(result['initial_stacks'])} don't match expected {expected_stacks}"


def test_kassatsu_multiplier_boost(mock_nin):
    """Test that Ninjutsu under Kassatsu gets a 1.3x multiplier."""
    # Instantiate NinjaActions with dummy parameters
    nin = NinjaActions({}, "dummy", 1, 1, 7.0)

    # Set Kassatsu buff window
    nin.meisui_times = np.array([[-1, -1]])
    nin.kassatsu_times = np.array([[500, 1000]])  # Kassatsu active from 500-1000

    # Create test DataFrame with Ninjutsu abilities inside and outside buff window
    df = pd.DataFrame(
        {
            "timestamp": [400, 750, 1100],
            "elapsed_time": [400, 750, 1100],
            "abilityGameID": 3 * [nin_id_map["Ninjutsu"]],
            "ability_name": 3 * ["Ninjutsu"],
            "action_name": 3 * ["Ninjutsu"],
            "buffs": [[], [], []],
            "multiplier": [1.0, 1.0, 1.0],
            "index": [0, 1, 2],
        }
    )
    df.set_index("index", inplace=True)

    result = nin.apply_ninja_buff(df)

    # Verify buff application and multipliers
    assert str(nin_id_map["Kassatsu"]) not in result.loc[0, "buffs"], "Ninjutsu before Kassatsu should not have buff"
    assert result.loc[0, "multiplier"] == 1.0, "Ninjutsu before Kassatsu should have 1.0x multiplier"

    assert str(nin_id_map["Kassatsu"]) in result.loc[1, "buffs"], "Ninjutsu during Kassatsu should have buff"
    assert result.loc[1, "multiplier"] == 1.3, "Ninjutsu during Kassatsu should have 1.3x multiplier"

    assert str(nin_id_map["Kassatsu"]) not in result.loc[2, "buffs"], "Ninjutsu after Kassatsu should not have buff"
    assert result.loc[2, "multiplier"] == 1.0, "Ninjutsu after Kassatsu should have 1.0x multiplier"


def test_kazematoi_ignored_for_pre_7_0(mock_nin):
    """Test that Kazematoi is ignored for patches before 7.0."""
    # Instantiate NinjaActions with patch 6.0
    nin = NinjaActions({}, "dummy", 1, 1, 6.0)

    # Create DataFrame with Aeolian Edge after Armor Crush (which would normally buff it)
    data = {
        "timestamp": [100, 200],
        "elapsed_time": [100, 200],
        "abilityGameID": [nin_id_map["Armor Crush"], nin_id_map["Aeolian Edge"]],
        "ability_name": ["Armor Crush", "Aeolian Edge"],
        "action_name": ["Armor Crush", "Aeolian Edge"],
        "buffs": [[], []],
        "multiplier": [1.0, 1.0],
        "index": [0, 1],
    }

    df = pd.DataFrame(data)
    df.set_index("index", inplace=True)

    result = nin.apply_ninja_buff(df)

    # Verify no buffs were applied since it's pre-7.0
    assert result.loc[1, "buffs"] == []
