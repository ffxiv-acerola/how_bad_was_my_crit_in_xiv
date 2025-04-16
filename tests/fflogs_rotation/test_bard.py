import pandas as pd
import pytest

from fflogs_rotation.bard import BardActions


@pytest.fixture
def bard_actions():
    return BardActions()


@pytest.mark.parametrize(
    "amount, multiplier, hit_type, direct_hit, main_stat_add, is_pitch_perfect, expected",
    [
        (1000, 1.0, 1, False, 0, False, 1000),
        (1500, 1.5, 1, False, 0, False, 1000),
        (1500, 1.0, 2, False, 0, False, 1000),
        (2250, 1.5, 2, False, 0, False, 1000),
        (1250, 1.0, 1, True, 0, False, 1000),
        (1875, 1.5, 1, True, 0, False, 1000),
        (1875, 1.0, 2, True, 0, False, 1000),
        (2813, 1.5, 2, True, 0, False, 1000),
        (1050, 1.0, 1, False, 300, True, 1000),
    ],
)
def test_normalize_damage(
    bard_actions,
    amount: int,
    multiplier: float,
    hit_type: int,
    direct_hit: bool,
    main_stat_add: int,
    is_pitch_perfect: bool,
    expected,
):
    l_c = 1500

    actions_df = pd.DataFrame(
        {
            "amount": [amount],
            "multiplier": [multiplier],
            "hitType": [hit_type],
            "directHit": [direct_hit],
            "main_stat_add": [main_stat_add],
        }
    )

    result = bard_actions._normalize_damage(actions_df, l_c, is_pitch_perfect)
    assert int(result["normalized_damage"].iloc[0]) == expected


@pytest.mark.parametrize("boundary_index, expected", [(1, 0.727), (2, 1.318), (3, None)])
def test_compute_potency_boundary(bard_actions, boundary_index, expected):
    if boundary_index == 3:
        with pytest.raises(ValueError):
            bard_actions._compute_potency_boundary(boundary_index)
    else:
        result = bard_actions._compute_potency_boundary(boundary_index)
        assert round(result, 3) == expected


@pytest.mark.parametrize(
    "actions_df, dmg_boundaries, expected",
    [
        (
            pd.DataFrame(
                {
                    "abilityGameID": [7404, 7404, 7404],
                    "relative_damage": [0.5, 1.0, 1.5],
                }
            ),
            {"dmg_boundary_1_2": 0.7, "dmg_boundary_2_3": 1.3},
            pd.DataFrame({"pp_buff": ["pp1", "pp2", "pp3"]}),
        )
    ],
)
def test_assign_pitch_perfect_stacks(bard_actions, actions_df, dmg_boundaries, expected):
    result = bard_actions._assign_pitch_perfect_stacks(actions_df, dmg_boundaries)
    pd.testing.assert_series_equal(result["pp_buff"], expected["pp_buff"])


@pytest.mark.parametrize(
    "actions_df_rows, expected_pp_name, expected_pp_buffs",
    [
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, []),
                (7404, "Pitch Perfect", 1636, 1, False, 1, 0, 1.2, []),
            ],
            "Pitch Perfect_pp3",
            ["pp3"],
        ),
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, []),
                (7404, "Pitch Perfect", 1000, 1, False, 1, 0, 1.2, []),
            ],
            "Pitch Perfect_pp2",
            ["pp2"],
        ),
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, []),
                (7404, "Pitch Perfect", 454, 1, False, 1, 0, 1.2, []),
            ],
            "Pitch Perfect_pp1",
            ["pp1"],
        ),
    ],
)
def test_estimate_pitch_perfect_potency(bard_actions, actions_df_rows, expected_pp_name, expected_pp_buffs):
    columns = [
        "abilityGameID",
        "action_name",
        "amount",
        "hitType",
        "directHit",
        "multiplier",
        "main_stat_add",
        "l_c",
        "buffs",
    ]

    actions_df = pd.DataFrame(actions_df_rows, columns=columns)
    result = bard_actions.estimate_pitch_perfect_potency(actions_df)
    action_name = result.iloc[-1]["action_name"]
    buffs = result.iloc[-1]["buffs"]

    # Function to test operates on action name and buff list
    assert action_name == expected_pp_name
    assert buffs == expected_pp_buffs


@pytest.mark.parametrize(
    "game_id, elapsed_time, buffs, expected",
    [
        (36977, 0.0, [], ["c1"]),
        (36977, 5.0, ["buff1"], ["c1", "buff1"]),
        (36977, 50.0, [], ["c3"]),
        (36977, 50.0, ["buff1"], ["c3", "buff1"]),
        (36977, 40.0, ["buff4"], ["buff4", "c3"]),
        (36979, 45.0, [], []),
        (36980, 0.0, ["buff4"], ["buff4"]),
    ],
)
def test_estimate_radiant_encore_potency(bard_actions, game_id: int, elapsed_time: float, buffs: list, expected):
    actions_df = pd.DataFrame(
        {
            "abilityGameID": [game_id],
            "elapsed_time": [elapsed_time],
            "buffs": [buffs],
        }
    )

    result = bard_actions.estimate_radiant_encore_potency(actions_df)
    # Order of buffs is irrelevant
    assert set(result.iloc[0]["buffs"]) == set(expected)
