"""Excluded enemy reference data and actor-ID resolution."""

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
