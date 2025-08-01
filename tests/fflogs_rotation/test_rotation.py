import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.rotation import ActionTable


class DummyAction(ActionTable):
    """
    A dummy subclass of ActionTable that overrides phase-related API calls.

    so that _process_fight_data() returns controlled values for testing.
    """

    def __init__(
        self,
    ):
        # encounter_phases is not used directly by _process_fight_data.
        self.encounter_phases = {1: {1: "Phase 1", 2: "Phase 2", 3: "Phase 3"}}

    def _fetch_phase_downtime(self, headers={}, phase_start_time=0, phase_end_time=0):
        # Return a dummy dict structure for downtime extraction.
        return {"table": {"data": {"downtime": 100}}}

    def _get_downtime(self, response: dict) -> int:
        # Extract downtime from the provided response.
        return response["table"]["data"].get("downtime", 0)


def create_fight_response(kill: bool, phases: int):
    """Simulate _fetchPhase_start_end_time based on the number phases and whether a kill happened.

    Args:
        kill (bool): _description_
        phases (int): _description_

    Returns:
        _type_: _description_
    """
    end_time_wipe = {0: 3000, 1: 4000, 2: 8000, 3: 13000}

    phase_transitions = [
        {"id": 1, "startTime": 100},
        {"id": 2, "startTime": 5000},
        {"id": 3, "startTime": 10000},
    ]

    if kill:
        end_time = 15000
    else:
        end_time = end_time_wipe[phases]
        phase_transitions = phase_transitions[0:phases]
    return {
        "potionType": {
            "data": {
                "auras": [],
            }
        },
        "startTime": 1000,  # Report start time in ms
        "table": {
            "data": {
                "downtime": 100,
            }
        },
        "fights": [
            {
                "encounterID": 1,
                "kill": kill,
                "startTime": 100,
                "endTime": end_time,
                "name": "Futures Rewritten",
                "hasEcho": False,
                "phaseTransitions": phase_transitions,
                "difficulty": 100,
            }
        ],
        "rankings": {
            "data": [
                {
                    "duration": 5000,
                },
            ]
        },
        "region": {"compactName": "JA"},
    }


@pytest.fixture
def action_table():
    return DummyAction()


@pytest.mark.parametrize(
    "phase, kill, expected",
    [
        (0, True, [1100, 16000, 14.80]),
        (1, True, [1100, 6000, 4.80]),
        (2, True, [6000, 11000, 4.9]),
        (3, True, [11000, 16000, 4.9]),
        (0, False, [1100, 4000, 2.8]),
        (1, False, [1100, 5000, 3.8]),
        (2, False, [6000, 9000, 2.9]),
        (3, False, [11000, 14000, 2.9]),
    ],
)
def test_fight_times(action_table, phase, kill, expected):
    """
    Test that fight times are properly calculated for a hypothetical three phase fight.

    Tests fight start time, fight end time, and dps active time for all phases
    and simulating a wipe at every phase.
    """
    action_table.phase = phase
    # Make phase response depending on the outcome
    # action_table.fight_info_response = create_fight_response(kill, phase)

    action_table._set_fight_information({}, create_fight_response(kill, phase))

    assert action_table.fight_start_time == expected[0]
    assert action_table.fight_end_time == expected[1]
    assert action_table.fight_dps_time == expected[2]


@pytest.mark.parametrize(
    "job, ranged_cards, melee_cards, input_card, expected_result",
    [
        # For a ranged job receiving a ranged card expect a 6% buff.
        ("WhiteMage", ["10003242"], [], "10003242", ("card6", 1.06)),
        # For a ranged job receiving a melee card expect a 3% buff.
        ("WhiteMage", [], ["10003242"], "10003242", ("card3", 1.03)),
        # For a melee job receiving a melee card expect a 6% buff.
        ("Ninja", [], ["11111111"], "11111111", ("card6", 1.06)),
        # For a melee job receiving a ranged card expect a 3% buff.
        ("Ninja", ["11111111"], [], "11111111", ("card3", 1.03)),
    ],
)
def test_ast_card_buff(job, ranged_cards, melee_cards, input_card, expected_result):
    instance = ActionTable.__new__(ActionTable)
    instance.job = job
    instance.ranged_cards = ranged_cards
    instance.melee_cards = melee_cards
    # Call the card buff function.
    result = instance.ast_card_buff(input_card)
    assert (
        result == expected_result
    ), f"For job {job} with card {input_card}, expected {expected_result} but got {result}"


@pytest.mark.parametrize(
    "phase, elapsed, expected",
    [
        (0, 50, "RadiantFinale1"),  # Phase 0, elapsed < 100 returns RadiantFinale1.
        (1, 75, "RadiantFinale1"),  # Phase 1, elapsed < 100 returns RadiantFinale1.
        (2, 50, "RadiantFinale3"),  # Phase 2 &, elapsed < 100 returns RadiantFinale3.
        (0, 150, "RadiantFinale3"),  # Phase 0, elapsed > 100 returns RadiantFinale3.
        (1, 200, "RadiantFinale3"),  # Phase 1, elapsed > 100 returns RadiantFinale3.
        (2, 150, "RadiantFinale3"),  # Phase 2, elapsed > 100 returns RadiantFinale3.
    ],
)
def test_estimate_radiant_finale_strength(phase, elapsed, expected):
    instance = ActionTable.__new__(ActionTable)
    instance.phase = phase
    result = instance.estimate_radiant_finale_strength(elapsed)
    assert result == expected, f"For phase {phase} and elapsed {elapsed}, expected {expected} but got {result}"


@pytest.fixture
def damage_buffs_df():
    # Create a damage_buffs DataFrame with buff_id and buff_strength.
    return pd.DataFrame(
        {
            "buff_id": [1, 2, 10],
            "buff_strength": [1.1, 1.2, 1.5],
        }
    )


@pytest.fixture
def actions_df_unique():
    """
    Create an actions DataFrame where one row already has a multiplier.

    This row should be preserved unmodified by _compute_multiplier_table.
    """
    data = {
        "buffs": [[10], [1, 2]],
        "multiplier": [1.5, np.nan],
    }
    return pd.DataFrame(data)


def test_compute_multiplier_table_existing_multiplier(actions_df_unique, damage_buffs_df):
    """
    If a multiplier is already present in the unique buff set,.

    _compute_multiplier_table should keep that multiplier.
    """
    instance = ActionTable.__new__(ActionTable)
    # Call the method.
    multiplier_table = instance._compute_multiplier_table(actions_df_unique, damage_buffs_df)

    # Convert buffs lists to strings as done within the method.
    multiplier_table = multiplier_table.reset_index(drop=True)

    # Find row with buffs equal to [10]
    for idx, row in multiplier_table.iterrows():
        if row["str_buffs"] == str([10]):
            # Multiplier is defined, so expect 1.5
            assert np.isclose(row["multiplier"], 1.5), f"Expected multiplier 1.5, got {row['multiplier']}"
            break
    else:
        pytest.fail("No row found with buffs [10]")


def test_compute_multiplier_table_remainder_calculation(actions_df_unique, damage_buffs_df):
    """
    For a row without a predefined multiplier, the multiplier should be computed from damage_buffs.

    In this test, for buffs [1,2], multiplier should equal 1.1 * 1.2 = 1.32.
    """
    instance = ActionTable.__new__(ActionTable)
    multiplier_table = instance._compute_multiplier_table(actions_df_unique, damage_buffs_df)
    multiplier_table = multiplier_table.reset_index(drop=True)

    for idx, row in multiplier_table.iterrows():
        if row["str_buffs"] == str([1, 2]):
            # Computed multiplier should be product of 1.1 and 1.2
            expected = 1.1 * 1.2
            assert np.isclose(row["multiplier"], expected), f"Expected multiplier {expected}, got {row['multiplier']}"
            break
    else:
        pytest.fail("No row found with buffs [1, 2]")


# Dummy Rate class to control the multiplier factor
class DummyRate:
    def __init__(self, crit_stat, dh_stat, level):
        self.crit_stat = crit_stat
        self.dh_stat = dh_stat
        self.level = level

    def get_hit_type_damage_buff(self, hit_type, buff_crit_rate, buff_dh_rate, determination):
        # If both rate buffs are zero, return factor 1.0 regardless
        if buff_crit_rate == 0 and buff_dh_rate == 0:
            return 1.0
        # For nonzero hit type (i.e. 1,2,3), return 1.2; else, return 1.0.
        if hit_type != 0:
            return 1.2
        return 1.0


@pytest.fixture(autouse=True)
def patch_rate(monkeypatch):
    # Monkeypatch the Rate class in rotation to our DummyRate.
    # FIXME: probably just instantiate a Rate instance in the class idk
    from fflogs_rotation import actions

    monkeypatch.setattr(actions, "Rate", DummyRate)


@pytest.fixture
def dummy_action_instance():
    # Create an instance of ActionTable with necessary attributes filled.
    instance = ActionTable.__new__(ActionTable)
    # Set some dummy stats
    instance.critical_hit_stat = 100
    instance.direct_hit_stat = 100
    instance.level = 80
    instance.determination = 200  # Determination value used in the multiplier calc
    # Default empty guaranteed hit type sources.
    instance.guaranteed_hit_type_via_buff = pd.DataFrame(columns=["buff_id", "affected_action_id", "hit_type"])
    instance.guaranteed_hit_type_via_action = {}
    return instance


def test_no_valid_hit_type(dummy_action_instance):
    """
    When there is no matching buff or action guarantee,.

    hit type remains 0 and multiplier is unchanged.
    """
    ability_id = "A"
    buff_ids = []  # no buffs are active
    base_multiplier = 1.5
    # ch and dh rates are nonzero but no valid trigger exists.
    new_multiplier, hit_type = dummy_action_instance.guaranteed_hit_type_damage_buff(
        ability_id, buff_ids, base_multiplier, ch_rate_buff=0.05, dh_rate_buff=0.05
    )
    # No valid hit type guarantee means no multiplier adjustment.
    assert np.isclose(new_multiplier, base_multiplier)
    assert hit_type == 0


def test_hit_type_via_buff(dummy_action_instance):
    """
    When a buff provides a guaranteed non-zero hit type,.

    the multiplier should be adjusted according to DummyRate.
    """
    ability_id = "A"
    # Create a dataframe indicating buff "B1" affects ability "A" with hit_type = 1.
    dummy_action_instance.guaranteed_hit_type_via_buff = pd.DataFrame(
        {
            "buff_id": ["B1"],
            "affected_action_id": [ability_id],
            "hit_type": [1],
        }
    )
    buff_ids = ["B1"]
    base_multiplier = 2.0
    # Provide nonzero rate buffs so DummyRate returns factor 1.2 for nonzero hit type.
    new_multiplier, hit_type = dummy_action_instance.guaranteed_hit_type_damage_buff(
        ability_id, buff_ids, base_multiplier, ch_rate_buff=0.1, dh_rate_buff=0.1
    )
    assert hit_type == 1
    assert np.isclose(new_multiplier, base_multiplier * 1.2)


def test_hit_type_via_action(dummy_action_instance):
    """
    When the action guarantee specifies a hit type via action,.

    the multiplier should be adjusted.
    """
    ability_id = "A"
    # Empty buff guarantee.
    dummy_action_instance.guaranteed_hit_type_via_buff = pd.DataFrame(
        columns=["buff_id", "affected_action_id", "hit_type"]
    )
    # Set guaranteed hit type via action dict.
    dummy_action_instance.guaranteed_hit_type_via_action = {ability_id: 2}
    buff_ids = []  # no buff provided
    base_multiplier = 3.0
    new_multiplier, hit_type = dummy_action_instance.guaranteed_hit_type_damage_buff(
        ability_id, buff_ids, base_multiplier, ch_rate_buff=0.1, dh_rate_buff=0.1
    )
    assert hit_type == 2
    assert np.isclose(new_multiplier, base_multiplier * 1.2)


def test_zero_rate_buffs_no_multiplier_change(dummy_action_instance):
    """
    When ch_rate and dh_rate are both zero, even if a guaranteed hit type is provided,.

    the multiplier should remain unchanged.
    """
    ability_id = "A"
    # Set up a guaranteed buff with nonzero hit type.
    dummy_action_instance.guaranteed_hit_type_via_buff = pd.DataFrame(
        {
            "buff_id": ["B1"],
            "affected_action_id": [ability_id],
            "hit_type": [1],
        }
    )
    buff_ids = ["B1"]
    base_multiplier = 2.5
    # Set ch_rate and dh_rate to 0.
    new_multiplier, hit_type = dummy_action_instance.guaranteed_hit_type_damage_buff(
        ability_id, buff_ids, base_multiplier, ch_rate_buff=0.0, dh_rate_buff=0.0
    )
    # Even though hit type is non-zero, DummyRate returns 1.0 if both rates are zero.
    assert hit_type == 1
    assert np.isclose(new_multiplier, base_multiplier * 1.0)
