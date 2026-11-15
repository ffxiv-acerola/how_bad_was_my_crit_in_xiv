"""Tests for validated FFLogs encounter response models."""

import pytest
from pydantic import AnyHttpUrl

from crit_app_v2.fflogs_encounters.models import (
    EncounterUrl,
    FFLogsEncounterFight,
    FFLogsPlayerDetails,
)


def test_encounter_fight_accepts_nullable_fields_and_float_timing():
    """Accept nullable FFLogs fields and fractional fight timestamps."""
    fight = FFLogsEncounterFight.model_validate(
        {
            "name": "Test encounter",
            "encounterID": 123,
            "kill": None,
            "startTime": 1000.5,
            "endTime": 2500.75,
            "combatTime": None,
            "lastPhase": None,
            "friendlyPets": None,
            "enemyNPCs": None,
        }
    )

    assert fight.start_time == 1000.5
    assert fight.end_time == 2500.75
    assert fight.kill is None
    assert fight.combat_time is None
    assert fight.last_phase is None
    assert fight.friendly_pets is None
    assert fight.enemy_npcs is None


def test_encounter_fight_accepts_nullable_npc_fields_and_list_entries():
    """Accept null NPC list entries and nullable IDs from FFLogs."""
    fight = FFLogsEncounterFight.model_validate(
        {
            "name": "Test encounter",
            "encounterID": 123,
            "kill": True,
            "startTime": 1000,
            "endTime": 2500,
            "combatTime": 1499.5,
            "lastPhase": 2,
            "friendlyPets": [None, {"id": None, "petOwner": None}],
            "enemyNPCs": [None, {"gameID": None, "id": None}],
        }
    )

    assert fight.friendly_pets is not None
    assert fight.friendly_pets[0] is None
    assert fight.friendly_pets[1] is not None
    assert fight.friendly_pets[1].id is None
    assert fight.friendly_pets[1].pet_owner is None
    assert fight.enemy_npcs is not None
    assert fight.enemy_npcs[0] is None
    assert fight.enemy_npcs[1] is not None
    assert fight.enemy_npcs[1].game_id is None
    assert fight.enemy_npcs[1].id is None
    assert fight.combat_time == 1499.5


def test_player_details_allows_a_role_group_to_be_missing():
    """Treat an omitted role group as empty report data rather than invalid."""
    player_details = FFLogsPlayerDetails.model_validate(
        {
            "tanks": [
                {
                    "name": "Tank Player",
                    "id": 4,
                    "server": "Hyperion",
                    "type": "Paladin",
                }
            ],
            "dps": [
                {
                    "name": "DPS Player",
                    "id": 5,
                    "server": "Cactuar",
                    "type": "Pictomancer",
                }
            ],
        }
    )

    assert player_details.tanks is not None
    assert player_details.tanks[0].job == "Paladin"
    assert player_details.dps is not None
    assert player_details.dps[0].job == "Pictomancer"
    assert player_details.healers is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.fflogs.com/reports/GpW6qnBmTML1zZC4?fight=last&type=damage-done",
        "https://de.fflogs.com/reports/GpW6qnBmTML1zZC4#fight=3",
    ],
    ids=["query", "fragment"],
)
def test_with_fight_id_builds_canonical_url(url):
    """Rebuild the URL on the same host with an explicit fight ID."""
    result = EncounterUrl(build_url=AnyHttpUrl(url)).with_fight_id(12)

    assert result.fight_id == 12
    assert result.report_id == "GpW6qnBmTML1zZC4"
    assert str(result.build_url).endswith("/reports/GpW6qnBmTML1zZC4?fight=12")
