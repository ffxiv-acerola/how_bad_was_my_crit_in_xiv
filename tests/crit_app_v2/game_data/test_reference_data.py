"""Tests for job-stat roles and range reference data."""

from crit_app_v2.game_data import ROLE_SPECS, SPEED_STAT_SPEC, STAT_INPUTS, Role, Stats


def test_role_specs_cover_every_role():
    """Ensure each role has corresponding framework-independent metadata."""
    assert set(ROLE_SPECS) == set(Role)


def test_stat_inputs_cover_every_stat_with_valid_ranges():
    """Ensure each stat has a valid canonical inclusive range."""
    assert set(STAT_INPUTS) == set(Stats)
    assert all(stat_input.lower <= stat_input.upper for stat_input in STAT_INPUTS.values())


def test_only_tanks_require_tenacity():
    """Ensure Tenacity requirements match the supported role rules."""
    assert ROLE_SPECS[Role.TANK].requires_tenacity
    assert all(not spec.requires_tenacity for role, spec in ROLE_SPECS.items() if role is not Role.TANK)


def test_each_role_has_labels_for_every_stat():
    """Ensure each role's explicit speed-stat reference resolves."""
    for role, role_spec in ROLE_SPECS.items():
        assert role_spec.main_stat_label.strip()
        assert role_spec.speed_stat in SPEED_STAT_SPEC
        assert SPEED_STAT_SPEC[role_spec.speed_stat].display_name.strip()
