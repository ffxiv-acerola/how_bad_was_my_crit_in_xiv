"""Tests for role-aware job-stat form labels."""

from crit_app_v2.game_data import STAT_INPUTS, Role, Stats
from crit_app_v2.ui.job_stats import _stat_input, player_analysis_job_build


def test_job_stat_inputs_have_labels_for_every_role():
    """Render a non-empty label for each stat input under every role."""
    for role in Role:
        for stat, stat_input in STAT_INPUTS.items():
            component = _stat_input(
                value=None,
                stat_input=stat_input,
                role=role,
                input_id=f"{role.value}-{stat.value}",
            )
            assert component.label.strip()


def test_role_aware_main_and_speed_stat_labels():
    """Use role metadata for the dynamic main-stat and speed labels."""
    healer_main = _stat_input(None, STAT_INPUTS[Stats.MAIN_STAT], Role.HEALER, "healer-main")
    healer_speed = _stat_input(None, STAT_INPUTS[Stats.SPEED_STAT], Role.HEALER, "healer-speed")
    melee_main = _stat_input(None, STAT_INPUTS[Stats.MAIN_STAT], Role.MELEE, "melee-main")

    assert healer_main.label == "Mind"
    assert healer_speed.label == "Spell speed"
    assert melee_main.label == "Strength/Dexterity"


def test_job_build_form_uses_unique_gearset_control_ids():
    """Keep the provider URL controls distinct from the FFLogs controls."""
    component = player_analysis_job_build()
    component_ids = {item.id for item in component._traverse() if getattr(item, "id", None) is not None}

    assert "gearset-url" in component_ids
    assert "gearset-url-button" in component_ids
    assert "fflogs-url" not in component_ids

    form_sections = component.children[0].children
    gear_selector_index = next(
        index for index, child in enumerate(form_sections) if getattr(child, "id", None) == "xiv-gear-select"
    )
    role_selector_index = next(
        index for index, child in enumerate(form_sections) if getattr(child, "id", None) == "role-select"
    )
    assert gear_selector_index < role_selector_index
