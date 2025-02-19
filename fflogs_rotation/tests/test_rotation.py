import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.rotation import ActionTable


# Dummy client that does nothing for our tests
class DummyClient:
    def query(self, query, variables, operationName=None):
        # For phase downtime queries, this will be overridden in tests via monkeypatching/lambda.
        return {}


# Common dummy response base for _process_fight_data tests with an encounter having 3 phases.
# The report contains a startTime, rankings with a duration, and a table.
def get_dummy_response(
    fight_name,
    encounter_id,
    kill,
    fight_start,
    fight_end,
    phase_transitions,
    table_data,
):
    return {
        "data": {
            "reportData": {
                "report": {
                    "startTime": 1000,
                    "fights": [
                        {
                            "name": fight_name,
                            "encounterID": encounter_id,
                            "hasEcho": False,
                            "kill": kill,
                            "phaseTransitions": phase_transitions,
                            "startTime": fight_start,  # relative fight start
                            "endTime": fight_end,  # relative fight end (used in phase=0 and final phase branch)
                        }
                    ],
                    "rankings": {"data": [{"duration": 5000}]},
                    "table": {"data": table_data},
                }
            }
        }
    }


# Define phase transitions for an encounter with 3 phases.
phase_transitions = [
    {"id": 1, "startTime": 2000},
    {"id": 2, "startTime": 4000},
    {"id": 3, "startTime": 8000},
]

# Set up encounter_phases mapping for the dummy instance
encounter_phases_dummy = {1: {1: "P1", 2: "P2", 3: "P3"}}


def test_process_fight_data_phase0():
    """Phase 0: No phase analysis performed; downtime from main response."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 0
    instance.client = DummyClient()
    instance.encounter_phases = encounter_phases_dummy

    # Dummy response with no downtime provided (default should be 0)
    dummy_response = get_dummy_response(
        fight_name="TestFight_phase0",
        encounter_id=1,
        kill=True,
        fight_start=1000,
        fight_end=12000,
        phase_transitions=phase_transitions,
        table_data={},  # No "downtime" key; _get_downtime will default to 0.
    )

    instance._process_fight_data(dummy_response, {})
    # Expected values:
    # report_start_time = 1000
    # phase branch is false so:
    #   fight_start_time = 1000 (report) + 1000 (fight start) = 2000
    #   fight_end_time = 1000 (report) + 5000 (fight end) = 6000
    #   downtime = 0, so fight_dps_time = (6000-2000-0)/1000 = 4.0

    assert instance.fight_name == "TestFight_phase0"
    assert instance.encounter_id == 1
    assert instance.has_echo is False
    assert instance.kill is True
    assert instance.report_start_time == 1000
    assert instance.fight_start_time == 2000
    assert instance.fight_end_time == 13000
    assert instance.downtime == 0
    assert instance.fight_dps_time == 11
    assert instance.ranking_duration == 5000
    assert instance.phase_start_time is None
    assert instance.phase_end_time is None


def test_process_fight_data_phase1():
    """Phase 1: Non-final phase using phaseTransitions (expected phase_start = 2000, phase_end = 4000)."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 1
    instance.client = DummyClient()
    instance.encounter_phases = encounter_phases_dummy

    # Patch _fetch_phase_downtime to return a dummy downtime response with downtime = 100.
    instance._fetch_phase_downtime = lambda: {
        "data": {"reportData": {"report": {"table": {"data": {"downtime": 100}}}}}
    }

    dummy_response = get_dummy_response(
        fight_name="TestFight_phase1",
        encounter_id=1,
        kill=True,
        fight_start=1000,  # These values are not used in phase branch for start/end times.
        fight_end=12000,  # fight_end is not used because _fetch_phase_start_end_time will select next phase start.
        phase_transitions=phase_transitions,
        table_data={},  # Not used in phase branch.
    )

    instance._process_fight_data(dummy_response, {})
    # _fetch_phase_start_end_time for phase==1:
    #   phase_start_time = when id==1 => 2000
    #   phase_end_time = when id==2 => 4000
    # Then:
    #   fight_start_time = report_start_time (1000) + 2000 = 3000
    #   fight_end_time   = report_start_time (1000) + 4000 = 5000
    #   downtime = 100, so fight_dps_time = (5000 - 3000 - 100)/1000 = 1.9
    assert instance.fight_name == "TestFight_phase1"
    assert instance.encounter_id == 1
    assert instance.has_echo is False
    assert instance.kill is True
    assert instance.report_start_time == 1000
    assert instance.phase_start_time == 2000
    assert instance.phase_end_time == 4000
    assert instance.fight_start_time == 3000
    assert instance.fight_end_time == 5000
    assert instance.downtime == 100
    assert pytest.approx(instance.fight_dps_time, 0.001) == 1.9
    assert instance.ranking_duration == 5000


def test_process_fight_data_phase2():
    """Phase 2: Non-final phase; expected phase_start = 4000, phase_end = 8000."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 2
    instance.client = DummyClient()
    instance.encounter_phases = encounter_phases_dummy

    # Patch _fetch_phase_downtime with dummy downtime = 150.
    instance._fetch_phase_downtime = lambda: {
        "data": {"reportData": {"report": {"table": {"data": {"downtime": 150}}}}}
    }

    dummy_response = get_dummy_response(
        fight_name="TestFight_phase2",
        encounter_id=1,
        kill=True,
        fight_start=1000,
        fight_end=12000,  # Irrelevant for non-final phase branch.
        phase_transitions=phase_transitions,
        table_data={},
    )

    instance._process_fight_data(dummy_response, {})
    # For phase==2:
    #   phase_start_time = when id==2 => 4000
    #   phase_end_time = when id==3 => 8000
    # Then:
    #   fight_start_time = 1000 + 4000 = 5000
    #   fight_end_time = 1000 + 8000 = 9000
    #   fight_dps_time = (9000 - 5000 - 150)/1000 = 3.85
    assert instance.fight_name == "TestFight_phase2"
    assert instance.encounter_id == 1
    assert instance.report_start_time == 1000
    assert instance.phase_start_time == 4000
    assert instance.phase_end_time == 8000
    assert instance.fight_start_time == 5000
    assert instance.fight_end_time == 9000
    assert instance.downtime == 150
    assert pytest.approx(instance.fight_dps_time, 0.001) == 3.85
    assert instance.ranking_duration == 5000


def test_process_fight_data_phase3():
    """Phase 3: Final phase (phase equals max phase) so phase_end_time returns fight["endTime"]."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 3
    instance.client = DummyClient()
    instance.encounter_phases = encounter_phases_dummy

    # Patch _fetch_phase_downtime with dummy downtime = 200.
    instance._fetch_phase_downtime = lambda: {
        "data": {"reportData": {"report": {"table": {"data": {"downtime": 200}}}}}
    }

    # For final phase, fight["endTime"] is used as phase_end_time.
    dummy_response = get_dummy_response(
        fight_name="TestFight_phase3",
        encounter_id=1,
        kill=True,
        fight_start=1000,
        fight_end=12000,  # This value will be used for phase_end_time in the final phase branch.
        phase_transitions=phase_transitions,
        table_data={},
    )

    instance._process_fight_data(dummy_response, {})
    # For phase==3:
    #   _fetch_phase_start_end_time will do:
    #       phase_start_time = when id==3 => 8000
    #       Since phase (3) is NOT less than max({1,2,3}) (3 < 3 is False), else branch applies:
    #         phase_end_time = fight_end_time from fight dict = 12000.
    # Then:
    #   fight_start_time = 1000 + 8000 = 9000
    #   fight_end_time = 1000 + 12000 = 13000
    #   fight_dps_time = (13000 - 9000 - 200)/1000 = 3.8
    assert instance.fight_name == "TestFight_phase3"
    assert instance.encounter_id == 1
    assert instance.report_start_time == 1000
    assert instance.phase_start_time == 8000
    assert instance.phase_end_time == 12000
    assert instance.fight_start_time == 9000
    assert instance.fight_end_time == 13000
    assert instance.downtime == 200
    assert pytest.approx(instance.fight_dps_time, 0.001) == 3.8
    assert instance.ranking_duration == 5000


def test_process_fight_data_phase1_wipe():
    """
    Multi-phase fight with a wipe in the first phase.

    Simulate a fight that did not progress past phase 1: Only one phase transition exists.
    In this case, even though encounter_phases indicates more phases,
    the missing next phase transition forces phase_end_time to be taken from fight["endTime"].
    """

    instance = ActionTable.__new__(ActionTable)
    instance.phase = 1
    instance.client = DummyClient()
    instance.encounter_phases = encounter_phases_dummy

    # Patch _fetch_phase_downtime and also _get_downtime to extract downtime.
    instance._fetch_phase_downtime = lambda: {
        "data": {"reportData": {"report": {"table": {"data": {"downtime": 50}}}}}
    }
    instance._get_downtime = lambda resp: resp["data"]["reportData"]["report"]["table"][
        "data"
    ]["downtime"]

    # Provide phase_transitions with only phase 1 information to simulate a wipe.
    reduced_phase_transitions = [
        {"id": 1, "startTime": 2000},
    ]
    dummy_response = get_dummy_response(
        fight_name="TestFight_phase1_wipe",
        encounter_id=1,
        kill=False,  # Wipe scenario; ranking_duration will be None.
        fight_start=1000,
        fight_end=9000,  # fight_end used as phase_end_time because next phase transition is missing.
        phase_transitions=reduced_phase_transitions,
        table_data={},
    )
    instance._process_fight_data(dummy_response, {})
    # Expected:
    #   phase_start_time = 2000 (from available phaseTransitions for id==1)
    #   phase_end_time   = fight["endTime"] = 9000 (since there's no transition for phase 2)
    #   fight_start_time = 1000+2000 = 3000
    #   fight_end_time   = 1000+9000 = 10000
    #   downtime = 50, so fight_dps_time = (10000 - 3000 - 50)/1000 = 6.95
    #   ranking_duration = None because kill is False.
    assert instance.fight_name == "TestFight_phase1_wipe"
    assert instance.encounter_id == 1
    assert instance.has_echo is False
    assert instance.kill is False
    assert instance.report_start_time == 1000
    assert instance.phase_start_time == 2000
    assert instance.phase_end_time == 9000
    assert instance.fight_start_time == 3000
    assert instance.fight_end_time == 10000
    assert instance.downtime == 50
    assert pytest.approx(instance.fight_dps_time, 0.001) == 6.95
    assert instance.ranking_duration is None


def test_ast_card_buff_ranged_receives_ranged_card():
    """
    For a ranged job (e.g., WhiteMage) receiving a ranged card,.

    expect a 6% damage buff.
    """
    instance = ActionTable.__new__(ActionTable)
    instance.job = "WhiteMage"
    instance.ranged_cards = ["10003242"]
    instance.melee_cards = []
    result = instance.ast_card_buff("10003242")
    assert result == ("card6", 1.06)


def test_ast_card_buff_ranged_receives_melee_card():
    """
    For a ranged job (e.g., WhiteMage) receiving a melee card,.

    expect a 3% damage buff.
    """
    instance = ActionTable.__new__(ActionTable)
    instance.job = "WhiteMage"
    instance.ranged_cards = []  # No ranged card present
    instance.melee_cards = ["10003242"]  # Card provided in melee_cards
    result = instance.ast_card_buff("10003242")
    assert result == ("card3", 1.03)


def test_ast_card_buff_melee_receives_melee_card():
    """
    For a melee job (e.g., Ninja) receiving a melee card,.

    expect a 6% damage buff.
    """
    instance = ActionTable.__new__(ActionTable)
    instance.job = "Ninja"
    instance.melee_cards = ["11111111"]
    instance.ranged_cards = []
    result = instance.ast_card_buff("11111111")
    assert result == ("card6", 1.06)


def test_ast_card_buff_melee_receives_ranged_card():
    """
    For a melee job (e.g., Ninja) receiving a ranged card,.

    expect a 3% damage buff.
    """
    instance = ActionTable.__new__(ActionTable)
    instance.job = "Ninja"
    instance.melee_cards = []  # No melee card present
    instance.ranged_cards = ["11111111"]  # Card provided in ranged_cards
    result = instance.ast_card_buff("11111111")
    assert result == ("card3", 1.03)


def test_estimate_radiant_finale_strength_phase0_under100():
    """For phase 0 and elapsed_time < 100, should return "RadiantFinale1"."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 0
    result = instance.estimate_radiant_finale_strength(50)
    assert result == "RadiantFinale1"


def test_estimate_radiant_finale_strength_phase1_under100():
    """For phase 1 and elapsed_time < 100, should return "RadiantFinale1"."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 1
    result = instance.estimate_radiant_finale_strength(75)
    assert result == "RadiantFinale1"


def test_estimate_radiant_finale_strength_phase2_under100():
    """
    For phase 2 and elapsed_time < 100, since phase > 1 the condition fails,.

    so it should return "RadiantFinale3".
    """
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 2
    result = instance.estimate_radiant_finale_strength(50)
    assert result == "RadiantFinale3"


def test_estimate_radiant_finale_strength_phase0_over100():
    """For phase 0 and elapsed_time > 100, should return "RadiantFinale3"."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 0
    result = instance.estimate_radiant_finale_strength(150)
    assert result == "RadiantFinale3"


def test_estimate_radiant_finale_strength_phase1_over100():
    """For phase 1 and elapsed_time > 100, should return "RadiantFinale3"."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 1
    result = instance.estimate_radiant_finale_strength(200)
    assert result == "RadiantFinale3"


def test_estimate_radiant_finale_strength_phase2_over100():
    """For phase 2 and elapsed_time > 100, should return "RadiantFinale3"."""
    instance = ActionTable.__new__(ActionTable)
    instance.phase = 2
    result = instance.estimate_radiant_finale_strength(150)
    assert result == "RadiantFinale3"


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


def test_compute_multiplier_table_existing_multiplier(
    actions_df_unique, damage_buffs_df
):
    """
    If a multiplier is already present in the unique buff set,.

    _compute_multiplier_table should keep that multiplier.
    """
    instance = ActionTable.__new__(ActionTable)
    # Call the method.
    multiplier_table = instance._compute_multiplier_table(
        actions_df_unique, damage_buffs_df
    )

    # Convert buffs lists to strings as done within the method.
    multiplier_table = multiplier_table.reset_index(drop=True)

    # Find row with buffs equal to [10]
    for idx, row in multiplier_table.iterrows():
        if row["str_buffs"] == str([10]):
            # Multiplier is defined, so expect 1.5
            assert np.isclose(
                row["multiplier"], 1.5
            ), f"Expected multiplier 1.5, got {row['multiplier']}"
            break
    else:
        pytest.fail("No row found with buffs [10]")


def test_compute_multiplier_table_remainder_calculation(
    actions_df_unique, damage_buffs_df
):
    """
    For a row without a predefined multiplier, the multiplier should be computed from damage_buffs.

    In this test, for buffs [1,2], multiplier should equal 1.1 * 1.2 = 1.32.
    """
    instance = ActionTable.__new__(ActionTable)
    multiplier_table = instance._compute_multiplier_table(
        actions_df_unique, damage_buffs_df
    )
    multiplier_table = multiplier_table.reset_index(drop=True)

    for idx, row in multiplier_table.iterrows():
        if row["str_buffs"] == str([1, 2]):
            # Computed multiplier should be product of 1.1 and 1.2
            expected = 1.1 * 1.2
            assert np.isclose(
                row["multiplier"], expected
            ), f"Expected multiplier {expected}, got {row['multiplier']}"
            break
    else:
        pytest.fail("No row found with buffs [1, 2]")


# Dummy Rate class to control the multiplier factor
class DummyRate:
    def __init__(self, crit_stat, dh_stat, level):
        self.crit_stat = crit_stat
        self.dh_stat = dh_stat
        self.level = level

    def get_hit_type_damage_buff(
        self, hit_type, buff_crit_rate, buff_dh_rate, determination
    ):
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
    from fflogs_rotation import rotation

    monkeypatch.setattr(rotation, "Rate", DummyRate)


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
    instance.guaranteed_hit_type_via_buff = pd.DataFrame(
        columns=["buff_id", "affected_action_id", "hit_type"]
    )
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
