"""Framework-independent encounter reference data.

Defines enemies whose damage FFLogs excludes for specific encounters, a
helper to resolve them to per-report actor IDs, and phase metadata.
"""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExcludedEnemyIDs:
    """Enemies whose damage FFLogs excludes for an encounter.

    Attributes
    ----------
    encounter_id
        FFLogs encounter ID.
    excluded_enemy_game_ids
        Game IDs of the enemies to exclude.
    """

    encounter_id: int
    excluded_enemy_game_ids: frozenset[int]


EXCLUDED_ENEMY_ID_SPEC: dict[int, ExcludedEnemyIDs] = {
    1079: ExcludedEnemyIDs(
        encounter_id=1079, excluded_enemy_game_ids=frozenset({17828})
    ),
    99: ExcludedEnemyIDs(encounter_id=99, excluded_enemy_game_ids=frozenset({18308})),
    1081: ExcludedEnemyIDs(
        encounter_id=1081, excluded_enemy_game_ids=frozenset({18701})
    ),
}


def get_excluded_enemy_ids(
    encounter_id: int,
    enemy_npcs: Iterable[tuple[int | None, int | None]],
) -> list[int]:
    """Resolve excluded enemy game IDs to FFLogs actor IDs.

    Parameters
    ----------
    encounter_id
        FFLogs encounter ID.
    enemy_npcs
        ``(game_id, actor_id)`` pairs for the enemies in the fight.

    Returns
    -------
    list[int]
        Actor IDs of enemies excluded for the encounter, in input order.
        Empty if the encounter has no exclusions. Pairs with a missing
        ``game_id`` or ``actor_id`` are skipped.
    """
    spec = EXCLUDED_ENEMY_ID_SPEC.get(encounter_id)
    if spec is None:
        return []

    return [
        actor_id
        for game_id, actor_id in enemy_npcs
        if game_id is not None
        and actor_id is not None
        and game_id in spec.excluded_enemy_game_ids
    ]


@dataclass(frozen=True)
class EncounterPhases:
    """Named phases for an encounter that supports phase-level analysis.

    Attributes
    ----------
    encounter_id
        FFLogs encounter ID.
    phase_names
        Phase labels in order; index 0 is phase 1.
    """

    encounter_id: int
    phase_names: tuple[str, ...]


@dataclass(frozen=True)
class PhaseOption:
    """A selectable analysis range.

    Attributes
    ----------
    value
        Phase number, where 0 means the entire fight.
    label
        Display label.
    """

    value: int
    label: str


ENCOUNTER_PHASES: dict[int, EncounterPhases] = {
    1079: EncounterPhases(
        1079,
        (
            "P1: Fatebreaker",
            "P2: Usurper of Frost",
            "P3: Oracle of Darkness",
            "P4: Enter the Dragon",
            "P5: Pandora",
        ),
    ),
    98: EncounterPhases(98, ("Phase 1", "Phase 2", "Phase 3")),
    99: EncounterPhases(99, ("Phase 1", "Phase 2", "Phase 3")),
    100: EncounterPhases(100, ("Phase 1", "Phase 2")),
}


def get_phase_options(
    encounter_id: int, last_phase_index: int | None
) -> list[PhaseOption]:
    """Build the phase choices for an encounter.

    Parameters
    ----------
    encounter_id
        FFLogs encounter ID.
    last_phase_index
        Furthest phase reached in the fight, or ``None`` if unknown.

    Returns
    -------
    list[PhaseOption]
        "Entire Fight" followed by phases 1 through the furthest phase reached.
        Only "Entire Fight" is returned for encounters without phase support.
    """
    options = [PhaseOption(0, "Entire Fight")]
    spec = ENCOUNTER_PHASES.get(encounter_id)
    if spec is None or not last_phase_index:
        return options

    reached = min(last_phase_index, len(spec.phase_names))
    options.extend(
        PhaseOption(index, spec.phase_names[index - 1])
        for index in range(1, reached + 1)
    )
    return options
