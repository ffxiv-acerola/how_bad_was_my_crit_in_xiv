"""Tests for FFLogs encounter presentation helpers."""

import pytest

from crit_app_v2.fflogs_encounters.models import Encounter
from crit_app_v2.game_data import Role
from crit_app_v2.ui.fflogs_encounter import (
    encounter_to_store,
    format_kill_time,
    job_selection,
    phase_select_state,
)

URL = "https://www.fflogs.com/reports/GpW6qnBmTML1zZC4?fight=37"


def _encounter(encounter_id=98, last_phase=2):
    """Build an encounter with players out of order."""

    def player(pid, job, role):
        return {
            "player_name": f"P{pid}",
            "player_server": "S",
            "player_id": pid,
            "pet_ids": [],
            "job": job,
            "role": role,
        }

    return Encounter.model_validate(
        {
            "encounter_url": {"build_url": URL},
            "fight_id_resolved": 37,
            "encounter_id": encounter_id,
            "encounter_name": "Boss",
            "last_phase_index": last_phase,
            "kill_time": 65.5,
            "excluded_enemy_ids": [],
            "players": [
                player(9, "Paladin", "Tank"),
                player(2, "Warrior", "Tank"),
                player(5, "WhiteMage", "Healer"),
            ],
            "limit_break": None,
        }
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "00:00.000"), (123.456, "02:03.456"), (65.5, "01:05.500")],
    ids=["zero", "minutes", "fraction"],
)
def test_format_kill_time(seconds, expected):
    """Format durations as mm:ss.mmm."""
    assert format_kill_time(seconds) == expected


def test_format_kill_time_rejects_negative():
    """Negative durations are invalid."""
    with pytest.raises(ValueError):
        format_kill_time(-1)


def test_encounter_store_round_trip():
    """A stored encounter validates back into the same model."""
    encounter = _encounter()

    assert Encounter.model_validate(encounter_to_store(encounter)) == encounter


@pytest.mark.parametrize(
    ("encounter_id", "visible"),
    [(98, True), (1, False)],
    ids=["phased", "unphased"],
)
def test_phase_select_state_visibility(encounter_id, visible):
    """Hide the phase selector when no phases are supported."""
    data, value, style = phase_select_state(_encounter(encounter_id))

    assert value == "0"
    assert (style["display"] == "block") is visible
    assert data[0] == {"value": "0", "label": "Entire Fight"}


def test_players_by_role_orders_roles_and_ids():
    """Roles follow enum order and players sort by FFLogs ID."""
    grouped = _encounter().players_by_role()

    assert list(grouped) == list(Role)
    assert [p.player_id for p in grouped[Role.TANK]] == [2, 9]
    assert grouped[Role.MELEE] == []


def test_job_selection_locks_to_role_and_clears_mismatch():
    """Only the selected role is enabled; mismatched selections are cleared."""
    group = job_selection(_encounter(), Role.TANK, selected_player_id="5")

    assert group.value is None
    radios = [radio for section in group.children.children for radio in section.children[1:]]
    assert {r.value: r.disabled for r in radios} == {
        "2": False,
        "9": False,
        "5": True,
    }
    assert job_selection(_encounter(), Role.TANK, "2").value == "2"
