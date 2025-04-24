import pandas as pd
import pytest

from fflogs_rotation.bard import BardActions


@pytest.fixture
def bard_actions():
    return BardActions(d2_100_potency=1000, patch_number=7.2)


@pytest.mark.parametrize("boundary_index, expected", [(1, 160.0), (2, 290.0), (3, None)])
def test_compute_potency_boundary(bard_actions, boundary_index, expected):
    if boundary_index == 3:
        with pytest.raises(ValueError):
            bard_actions._compute_potency_boundary(boundary_index)
    else:
        result = bard_actions._compute_potency_boundary(boundary_index)
        assert result == expected


@pytest.mark.parametrize(
    "actions_df_rows, expected_pp_buffs",
    [
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, [], 0, 200),
                (7404, "Pitch Perfect", 1636, 1, False, 1, 0, 1.2, [], 1, 370),
            ],
            ["pp3"],
        ),
        # Pitch perfect with multi target falloff,
        # same packetID, so PP3 is still applied.
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, [], 0, 200),
                (7404, "Pitch Perfect", 1636, 1, False, 1, 0, 1.2, [], 1, 370),
                (7404, "Pitch Perfect", 800, 1, False, 1, 0, 1.2, [], 1, 150),
            ],
            ["pp3"],
        ),
        (
            [
                (7404, "Pitch Perfect", 1000, 1, False, 1, 0, 1.2, [], 1, 220),
            ],
            ["pp2"],
        ),
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, [], 0, 200),
                (7404, "Pitch Perfect", 454, 1, False, 1, 0, 1.2, [], 1, 100),
            ],
            ["pp1"],
        ),
    ],
)
def test_estimate_pitch_perfect_potency(bard_actions, actions_df_rows, expected_pp_buffs):
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
        "packetID",
        "estimated_potency",
    ]

    actions_df = pd.DataFrame(actions_df_rows, columns=columns)
    result = bard_actions.estimate_pitch_perfect_potency(actions_df)
    buffs = result.iloc[-1]["buffs"]
    action_name = result.iloc[-1]["action_name"]
    expected_name = f"Pitch Perfect_{expected_pp_buffs[0]}"

    # Function to test operates on action name and buff list
    assert action_name == expected_name
    assert buffs == expected_pp_buffs


@pytest.mark.parametrize(
    "actions_df_rows, expected_gauge_buffs",
    [
        (
            [
                (16496, "Apex Arrow", 2000, 1, False, 1, 0, 1.2, [], 1, 600),
            ],
            ["gauge_100"],
        ),
        (
            [
                (16496, "Apex Arrow", 1400, 1, False, 1, 0, 1.2, [], 2, 350),
            ],
            ["gauge_60"],
        ),
        # Multi-target case with same packetID should use averaged potency
        (
            [
                (16496, "Apex Arrow", 1200, 1, False, 1, 0, 1.2, [], 3, 300),
                (16496, "Apex Arrow", 1100, 1, False, 1, 0, 1.2, [], 3, 290),
            ],
            ["gauge_50"],
        ),
        (
            [
                (16495, "Burst Shot", 1000, 1, False, 1, 0, 1.2, [], 4, 220),
                (16496, "Apex Arrow", 800, 1, False, 1, 0, 1.2, [], 5, 200),
            ],
            ["gauge_35"],
        ),
    ],
)
def test_estimate_apex_arrow_potency(bard_actions, actions_df_rows, expected_gauge_buffs):
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
        "packetID",
        "estimated_potency",
    ]

    actions_df = pd.DataFrame(actions_df_rows, columns=columns)
    result = bard_actions.estimate_apex_arrow_potency(actions_df)

    # Filter for Apex Arrow entries
    apex_rows = result[result["abilityGameID"] == 16496]

    if not apex_rows.empty:
        buffs = apex_rows.iloc[-1]["buffs"]
        action_name = apex_rows.iloc[-1]["action_name"]
        expected_name = f"Apex Arrow_{expected_gauge_buffs[0]}"

        # Verify action name and buffs
        assert action_name == expected_name
        assert buffs == expected_gauge_buffs


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
