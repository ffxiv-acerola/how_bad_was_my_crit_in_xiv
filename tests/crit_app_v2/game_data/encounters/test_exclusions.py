"""Tests for excluded enemy reference data."""

import pytest

from crit_app_v2.game_data.encounters import EXCLUDED_ENEMY_ID_SPEC, get_excluded_enemy_ids


def test_spec_keys_match_encounter_ids():
    """Each spec is keyed by its own encounter ID."""
    for key, spec in EXCLUDED_ENEMY_ID_SPEC.items():
        assert key == spec.encounter_id


@pytest.mark.parametrize(
    ("encounter_id", "enemy_npcs", "expected"),
    [
        (1, [(17828, 5)], []),
        (1079, [], []),
        (1079, [(1, 5), (2, 6)], []),
        (1079, [(1, 5), (17828, 6)], [6]),
        (1079, [(17828, 6), (17828, 9)], [6, 9]),
        (1079, [(None, 5), (17828, None)], []),
        (99, [(18308, 3), (17828, 4)], [3]),
    ],
    ids=[
        "unknown encounter",
        "no npcs",
        "no matches",
        "single match",
        "multiple matches",
        "missing ids skipped",
        "other encounter's game ids ignored",
    ],
)
def test_get_excluded_enemy_ids(encounter_id, enemy_npcs, expected):
    """Resolve excluded game IDs to actor IDs for an encounter."""
    assert get_excluded_enemy_ids(encounter_id, enemy_npcs) == expected
