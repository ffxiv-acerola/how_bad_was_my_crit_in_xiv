"""Tests for encounter metadata and analysis support."""

import pytest

from crit_app_v2.game_data.encounters import (
    ENCOUNTER_PHASES,
    ENCOUNTER_SPECS,
    EXCLUDED_ENEMY_ID_SPEC,
    get_encounter_spec,
    is_party_analyzeable,
    is_player_analyzeable,
)


def test_encounter_specs_keys_and_values():
    """Specs are keyed by ID, have unique short names, and valid levels."""
    short_names = [spec.short_name for spec in ENCOUNTER_SPECS.values()]

    for key, spec in ENCOUNTER_SPECS.items():
        assert key == spec.encounter_id
        assert spec.level in (90, 100)
    assert len(short_names) == len(set(short_names))


def test_encounter_specs_match_legacy_tables():
    """Specs cover the legacy valid encounters with matching levels."""
    from crit_app.job_data.encounter_data import encounter_level, valid_encounters

    assert set(ENCOUNTER_SPECS) == set(valid_encounters)
    for encounter_id, spec in ENCOUNTER_SPECS.items():
        assert spec.level == encounter_level[encounter_id]


def test_related_reference_data_has_specs():
    """Phase and exclusion data only exist for supported encounters."""
    assert set(ENCOUNTER_PHASES) <= set(ENCOUNTER_SPECS)
    assert set(EXCLUDED_ENEMY_ID_SPEC) <= set(ENCOUNTER_SPECS)


@pytest.mark.parametrize(
    ("encounter_id", "expected"),
    [(1079, True), (1071, False), (-1, False)],
    ids=["supported", "legacy unsupported", "unknown"],
)
def test_analyzeable_helpers(encounter_id, expected):
    """Unknown encounters are not analyzeable; specs allow both by default."""
    assert is_player_analyzeable(encounter_id) is expected
    assert is_party_analyzeable(encounter_id) is expected
    assert (get_encounter_spec(encounter_id) is not None) is expected
