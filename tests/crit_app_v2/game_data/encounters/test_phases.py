"""Tests for encounter phase reference data."""

import pytest

from crit_app_v2.game_data.encounters import ENCOUNTER_PHASES, get_phase_options


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
