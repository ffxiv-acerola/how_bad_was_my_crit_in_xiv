"""Calculations and utilities for player-level analysis workflows."""

from crit_app_v2.fflogs_encounters.models import Encounter

DISCRETIZATION_LEVEL_MAP = {90: 4, 100: 10}


def compute_party_bonus(encounter: Encounter) -> float:
    """Calculate the 1% party bonus for each distinct player role.

    Parameters
    ----------
    encounter
        Server-validated encounter and player roster.

    Returns
    -------
    float
        Party multiplier, from 1.0 to 1.05. Limit Break is not included in
        ``encounter.players`` and therefore does not contribute.
    """
    return 1.0 + len({player.role for player in encounter.players}) / 100


def correct_final_phase(fight_phase: int, last_phase_index: int | None) -> int:
    """Clamp a requested phase to the last phase reached in the encounter.

    Parameters
    ----------
    fight_phase
        Requested phase, where 0 means the entire fight.
    last_phase_index
        Furthest phase reached, or None when FFLogs did not provide one.

    Returns
    -------
    int
        Requested phase clamped to the last reached phase when available.
    """
    if last_phase_index is not None and fight_phase > last_phase_index:
        return last_phase_index
    return fight_phase
