"""Tests for role metadata used by build models."""

from crit_app_v2.game_data import ROLE_SPECS, SPEED_STAT_SPEC, Role


def test_role_specs_are_complete_and_framework_independent():
    """Ensure every role has resolved, framework-independent metadata."""
    assert set(ROLE_SPECS) == set(Role)
    assert ROLE_SPECS[Role.TANK].requires_tenacity
    assert all(not spec.requires_tenacity for role, spec in ROLE_SPECS.items() if role is not Role.TANK)
    assert all(spec.main_stat_label.strip() for spec in ROLE_SPECS.values())
    assert all(SPEED_STAT_SPEC[spec.speed_stat].display_name.strip() for spec in ROLE_SPECS.values())
