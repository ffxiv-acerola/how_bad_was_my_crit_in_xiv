import pandas as pd
from pandas.testing import assert_frame_equal

from fflogs_rotation.ninja import (
    NinjaActionsDawntrail,
)


def test_ew_meisui_buffs():
    pass


def test_dt_kazematoi_gauge():
    """Test the number of Kazematoi stacks is correctly generated and consumed.

    Test cases:
    - Filter non-kazematoi actions and columns
    - 3 stacks -> 5 stacks
    - 4 stacks -> 5 stacks
    - 5 stacks -> 5 stacks
    - 1 stacks -> 0 stacks
    - 0 stacks -> 0 stacks
    - 1 stacks -> 3 stacks
    - 3 stacks -> 2 stacks
    """

    input_df = pd.DataFrame(
        [
            (1, [], 2255, "Aeolian Edge"),
            (2, [], 2255, "Aeolian Edge"),
            (3, [], 3563, "Armor Crush"),
            (4, [], 2255, "Aeolian Edge"),
            (5, [], 3563, "Armor Crush"),
            (6, [], 3563, "Armor Crush"),
            (7, [], 3563, "Armor Crush"),
            (8, [], 1234, "Extra action"),
            (9, [], 2255, "Aeolian Edge"),
            (10, [], 2255, "Aeolian Edge"),
            (11, [], 2255, "Aeolian Edge"),
            (12, [], 2255, "Aeolian Edge"),
            (13, [], 2255, "Aeolian Edge"),
            (14, [], 2255, "Aeolian Edge"),
            (15, [], 2255, "Aeolian Edge"),
        ],
        columns=["elapsed_time", "buffs", "abilityGameID", "ability_name"],
    )

    # Hand-calculated values
    change = [-1, -1, 2, -1, 2, 2, 2, -1, -1, -1, -1, -1, -1, -1]
    stacks = [0, 0, 0, 2, 1, 3, 5, 5, 4, 3, 2, 1, 0, 0]

    expected_df = input_df.copy().drop(columns=["buffs"])
    expected_df = expected_df[expected_df["abilityGameID"].isin([2255, 3563])]
    expected_df["change"] = change
    expected_df["initial_stacks"] = stacks

    test_output = NinjaActionsDawntrail()._track_kazematoi_gauge(input_df)

    # `check_like=True`` ignores column order.
    assert_frame_equal(test_output, expected_df, check_like=True)

    # RotationTable(
    #     headers,
    #     "F4Z8zaCxKMWpJRd1",
    #     2,
    #     "Ninja",
    #     3,
    #     2557,
    #     1432,
    #     1844,
    #     254,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     potency_table,
    #     pet_ids=None,
    # )
