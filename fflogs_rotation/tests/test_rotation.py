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

    instance._process_fight_data(dummy_response)
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

    instance._process_fight_data(dummy_response)
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

    instance._process_fight_data(dummy_response)
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

    instance._process_fight_data(dummy_response)
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
    instance._process_fight_data(dummy_response)
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
