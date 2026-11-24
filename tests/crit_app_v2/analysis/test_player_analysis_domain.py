"""Tests for domain calculations and validation of player-analysis inputs."""

import pytest
from pydantic import AnyHttpUrl

from crit_app_v2.analysis.player_analysis import compute_party_bonus, correct_final_phase
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)
from crit_app_v2.game_data import Job, Role


def _encounter(roles: list[Role]) -> Encounter:
    """Build an encounter with one valid job for each requested role."""
    job_by_role = {
        Role.TANK: Job.WARRIOR,
        Role.HEALER: Job.WHITE_MAGE,
        Role.MELEE: Job.DRAGOON,
        Role.PHYSICAL_RANGED: Job.BARD,
        Role.MAGICAL_RANGED: Job.BLACK_MAGE,
    }
    players = [
        EncounterPersonnel(
            player_name=f"Player {index}",
            player_server="Test Server",
            player_id=index,
            pet_ids=[],
            job=job_by_role[role],
            role=role,
        )
        for index, role in enumerate(roles, start=1)
    ]
    return Encounter(
        encounter_url=EncounterUrl(build_url=AnyHttpUrl("https://www.fflogs.com/reports/abcdefghijklmnop?fight=7")),
        fight_id_resolved=7,
        encounter_id=93,
        encounter_name="Black Cat",
        last_phase_index=0,
        kill_time=100,
        excluded_enemy_ids=[],
        players=players,
        limit_break=None,
    )


@pytest.mark.parametrize(
    ("roles", "expected_bonus"),
    [
        ([Role.TANK, Role.TANK], 1.01),
        ([Role.TANK, Role.HEALER, Role.MELEE], 1.03),
        ([Role.TANK, Role.HEALER, Role.MELEE, Role.PHYSICAL_RANGED, Role.MAGICAL_RANGED], 1.05),
    ],
    ids=["duplicate-role", "three-roles", "all-roles"],
)
def test_compute_party_bonus_counts_unique_roles(roles: list[Role], expected_bonus: float) -> None:
    """Add one percentage point per distinct role in the player roster."""
    assert compute_party_bonus(_encounter(roles)) == expected_bonus


@pytest.mark.parametrize(
    ("phase", "last_phase", "expected"),
    [(5, 2, 2), (1, 2, 1), (3, None, 3)],
    ids=["clamps-final-phase", "keeps-valid-phase", "unknown-last-phase"],
)
def test_correct_final_phase_handles_encounter_phase_bounds(phase: int, last_phase: int | None, expected: int) -> None:
    """Clamp phases only when an encounter provides a furthest phase."""
    assert correct_final_phase(phase, last_phase) == expected
