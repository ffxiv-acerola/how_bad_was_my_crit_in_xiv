"""Tests for encounter reference data."""

import pytest

from crit_app_v2.game_data.encounters import (
    ENCOUNTER_PHASES,
    EXCLUDED_ENEMY_ID_SPEC,
    get_excluded_enemy_ids,
    get_phase_options,
)


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


@pytest.mark.parametrize(
    ("encounter_id", "last_phase", "expected_values"),
    [
        (1, 3, [0]),
        (98, None, [0]),
        (98, 0, [0]),
        (98, 2, [0, 1, 2]),
        (98, 3, [0, 1, 2, 3]),
        (98, 9, [0, 1, 2, 3]),
        (1079, 5, [0, 1, 2, 3, 4, 5]),
    ],
    ids=[
        "unsupported encounter",
        "unknown last phase",
        "no phases reached",
        "partial kill",
        "full kill",
        "phase beyond known names",
        "ultimate five phases",
    ],
)
def test_get_phase_options(encounter_id, last_phase, expected_values):
    """Offer the entire fight plus each reached phase when supported."""
    options = get_phase_options(encounter_id, last_phase)

    assert [option.value for option in options] == expected_values
    assert options[0].label == "Entire Fight"


def test_encounter_phases_keys_match_ids():
    """Each phase spec is keyed by its own encounter ID."""
    for key, spec in ENCOUNTER_PHASES.items():
        assert key == spec.encounter_id
