"""Tests for the saved-gearset callbacks."""

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict
from dash.exceptions import PreventUpdate

from crit_app_v2.build_providers import BuildProvider
from crit_app_v2.game_data import ROLE_SPECS, STAT_INPUTS, Role, Stats
from crit_app_v2.gearsets import (
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    SavedGearset,
    library_from_storage,
    library_to_storage,
)

with patch("dash.register_page"):
    from crit_app_v2.callbacks import gearsets as callbacks
    from crit_app_v2.pages.analysis import apply_loaded_job_build
from crit_app_v2.ui.gearset_manager import (
    DEFAULT_TYPE,
    DELETE_TYPE,
    SELECT_TYPE,
    UPDATE_TYPE,
    gearset_pattern_id,
)

STAT_ORDER = (
    Stats.MAIN_STAT,
    Stats.DETERMINATION,
    Stats.SPEED_STAT,
    Stats.CRITICAL_HIT,
    Stats.DIRECT_HIT,
    Stats.WEAPON_DAMAGE,
    Stats.TENACITY,
)


@contextmanager
def triggered(prop_id, value=1):
    """Run code as though one Dash input, identified by ``prop_id``, fired."""
    token = context_value.set(AttributeDict(triggered_inputs=[{"prop_id": prop_id, "value": value}]))
    try:
        yield
    finally:
        context_value.reset(token)


def pattern_prop(component_type, gearset_id, prop="n_clicks", cell=None):
    """Build the prop ID Dash reports for a pattern-matching component."""
    pattern = gearset_pattern_id(component_type, gearset_id, cell)
    return f"{json.dumps(pattern, separators=(',', ':'), sort_keys=True)}.{prop}"


def form(role=Role.HEALER, offset=0):
    """Return the form's positional stat values (role excluded) for a role."""
    values = {stat: STAT_INPUTS[stat].lower + offset for stat in Stats}
    if not ROLE_SPECS[role].requires_tenacity:
        values[Stats.TENACITY] = None
    return tuple(values[stat] for stat in STAT_ORDER)


def make_gearset(name="Set", role=Role.HEALER, offset=0):
    """Create a valid gearset."""
    return SavedGearset.from_form_values(name, role, dict(zip(STAT_ORDER, form(role, offset), strict=True)))


def stored(*gearsets, default=None):
    """Create stored library data from gearsets."""
    return library_to_storage(GearsetLibrary(gearsets=gearsets, default_id=default.id if default else None))


def test_initialize_migrates_legacy_data_when_library_is_missing():
    """Import legacy gearsets once into the new library store."""
    legacy = [
        {
            "role": "Healer",
            "name": "Old",
            "main_stat": 4000,
            "determination": 2000,
            "speed": 500,
            "crit": 2500,
            "direct_hit": 1000,
            "weapon_damage": 140,
        }
    ]

    library_data, selected, build = callbacks.initialize_gearsets(True, None, legacy, 0)

    library = library_from_storage(library_data)
    assert [g.name for g in library.gearsets] == ["Old"]
    assert library.default_gearset.name == "Old"
    assert selected == library.default_id
    assert build["build_provider"] == BuildProvider.INTERNAL
    assert build["build_name"] == "Old"


def test_initialize_does_not_rewrite_existing_library():
    """Leave an existing library untouched and ignore legacy stores."""
    gearset = make_gearset()

    library_data, selected, build = callbacks.initialize_gearsets(
        True, stored(gearset), [{"role": "Healer", "name": "Ignored"}], None
    )

    assert library_data is no_update
    assert (selected, build) == (no_update, no_update)


def test_initialize_writes_empty_library_for_new_users():
    """Create an empty library so later callbacks always find valid data."""
    library_data, selected, build = callbacks.initialize_gearsets(True, None, None, None)

    assert library_from_storage(library_data).gearsets == ()
    assert (selected, build) == (no_update, no_update)


def test_initialize_replaces_corrupt_library():
    """Fall back to a fresh library when stored data is unreadable."""
    library_data, *_ = callbacks.initialize_gearsets(True, {"garbage": True}, None, None)

    assert library_from_storage(library_data) is not None


def test_initialize_applies_default_to_a_new_analysis():
    """Load the default gearset into the form for a new analysis."""
    default = make_gearset("Default", Role.TANK)

    _, selected, build = callbacks.initialize_gearsets(
        True, stored(make_gearset("Other"), default, default=default), None, None
    )

    assert selected == default.id
    assert build["build_role"] == "Tank"


def test_initialize_never_applies_default_to_a_saved_analysis():
    """Keep a saved analysis's stats when a default gearset exists."""
    default = make_gearset("Default")

    library_data, selected, build = callbacks.initialize_gearsets(False, stored(default, default=default), None, None)

    assert (library_data, selected, build) == (no_update,) * 3


def test_initialize_still_migrates_for_a_saved_analysis():
    """Migrate legacy data even when the default is not applied."""
    legacy = [
        {
            "role": "Healer",
            "name": "Old",
            "main_stat": 4000,
            "determination": 2000,
            "speed": 500,
            "crit": 2500,
            "direct_hit": 1000,
            "weapon_damage": 140,
        }
    ]

    library_data, selected, build = callbacks.initialize_gearsets(False, None, legacy, 0)

    assert len(library_from_storage(library_data).gearsets) == 1
    assert (selected, build) == (no_update, no_update)


def test_render_reports_rows_and_loaded_label():
    """Render table rows and name the loaded gearset."""
    gearset = make_gearset("Mine")

    rows, badge = callbacks.render_gearsets(stored(gearset), gearset.id)

    assert len(rows) == 1
    assert badge.children.children == "Mine"


def test_render_tolerates_missing_library():
    """Render an empty table before the library has been initialized."""
    rows, badge = callbacks.render_gearsets(None, None)

    assert len(rows) == 1
    assert badge is None


@pytest.mark.parametrize(
    ("name", "role", "offset", "expected_disabled"),
    [
        ("Name", Role.HEALER, 0, False),
        ("", Role.HEALER, 0, True),
        ("   ", Role.HEALER, 0, True),
        ("Name", Role.HEALER, -1, True),
    ],
    ids=["valid", "no-name", "blank-name", "out-of-range-stat"],
)
def test_save_button_requires_name_and_valid_stats(name, role, offset, expected_disabled):
    """Enable saving only for a named form with valid stats."""
    disabled = callbacks.enable_save_new_gearset(name, role.value, *form(role, offset), None)

    assert disabled is expected_disabled


def test_save_button_requires_tenacity_for_tanks():
    """Disable saving a Tank without Tenacity."""
    values = list(form(Role.TANK))
    values[-1] = None

    assert callbacks.enable_save_new_gearset("Name", "Tank", *values, None) is True


def test_save_button_disabled_when_library_is_full():
    """Disable saving once the library holds the maximum number of gearsets."""
    full = stored(*[make_gearset(f"Set {i}") for i in range(MAX_SAVED_GEARSETS)])

    assert callbacks.enable_save_new_gearset("Name", "Healer", *form(), full) is True


def test_save_new_gearset_selects_it_and_clears_the_name():
    """Add the form's stats as a new gearset and select it."""
    existing = make_gearset("Existing")

    library_data, selected, name_value, message = callbacks.save_new_gearset(
        1, "  New  ", "Healer", *form(offset=5), stored(existing)
    )

    library = library_from_storage(library_data)
    assert [g.name for g in library.gearsets] == ["Existing", "New"]
    assert selected == library.gearsets[1].id
    assert (name_value, message) == ("", None)
    assert library.gearsets[1].stats.main_stat == STAT_INPUTS[Stats.MAIN_STAT].lower + 5


def test_save_new_gearset_allows_duplicate_names():
    """Allow a new gearset to reuse an existing name."""
    existing = make_gearset("Same")

    library_data, *_ = callbacks.save_new_gearset(1, "Same", "Healer", *form(), stored(existing))

    assert [g.name for g in library_from_storage(library_data).gearsets] == ["Same", "Same"]


def test_save_new_gearset_drops_hidden_tenacity():
    """Ignore stale Tenacity when saving a non-Tank gearset."""
    values = list(form())
    values[-1] = 999

    library_data, *_ = callbacks.save_new_gearset(1, "Healer", "Healer", *values, None)

    assert library_from_storage(library_data).gearsets[0].stats.tenacity is None


def test_save_new_gearset_reports_invalid_stats_without_changing_anything():
    """Show a message and keep data and name when stats are invalid."""
    values = list(form())
    values[0] = None

    result = callbacks.save_new_gearset(1, "Name", "Healer", *values, None)

    assert result[:3] == (no_update,) * 3
    assert "valid" in result[3]


def test_save_new_gearset_reports_full_library():
    """Show a message when the library is full."""
    full = stored(*[make_gearset(f"Set {i}") for i in range(MAX_SAVED_GEARSETS)])

    result = callbacks.save_new_gearset(1, "Name", "Healer", *form(), full)

    assert result[:3] == (no_update,) * 3
    assert "up to" in result[3]


def test_save_new_gearset_ignores_unclicked_button():
    """Do nothing when the callback fires without a click."""
    with pytest.raises(PreventUpdate):
        callbacks.save_new_gearset(None, "Name", "Healer", *form(), None)


def test_update_gearset_replaces_stats_but_keeps_name_and_position():
    """Overwrite the clicked gearset's stats and role, keeping its name and ID."""
    first, second = make_gearset("First"), make_gearset("Second")

    with triggered(pattern_prop(UPDATE_TYPE, first.id)):
        library_data, selected, message = callbacks.update_gearset(
            [1, None], "Tank", *form(Role.TANK, 7), stored(first, second)
        )

    library = library_from_storage(library_data)
    assert [g.id for g in library.gearsets] == [first.id, second.id]
    assert library.gearsets[0].name == "First"
    assert library.gearsets[0].role is Role.TANK
    assert library.gearsets[0].stats.tenacity == STAT_INPUTS[Stats.TENACITY].lower + 7
    assert library.gearsets[1] == second
    assert (selected, message) == (first.id, None)


def test_update_gearset_rejects_invalid_form_values():
    """Refuse to overwrite a saved gearset with an incomplete form."""
    gearset = make_gearset()
    values = list(form())
    values[3] = None

    with triggered(pattern_prop(UPDATE_TYPE, gearset.id)):
        result = callbacks.update_gearset([1], "Healer", *values, stored(gearset))

    assert result[:2] == (no_update, no_update)
    assert "valid" in result[2]


def test_update_gearset_for_missing_gearset_reports_it():
    """Report a gearset deleted elsewhere instead of failing."""
    with triggered(pattern_prop(UPDATE_TYPE, "11111111-1111-4111-8111-111111111111")):
        result = callbacks.update_gearset([1], "Healer", *form(), stored(make_gearset()))

    assert result[:2] == (no_update, no_update)
    assert "no longer exists" in result[2]


def test_pattern_callbacks_ignore_rerender_triggers():
    """Ignore zero-click triggers caused by re-rendering the table's buttons."""
    gearset = make_gearset()

    with triggered(pattern_prop(UPDATE_TYPE, gearset.id), value=0), pytest.raises(PreventUpdate):
        callbacks.update_gearset([0], "Healer", *form(), stored(gearset))
    with triggered(pattern_prop(SELECT_TYPE, gearset.id), value=0), pytest.raises(PreventUpdate):
        callbacks.select_gearset([0], stored(gearset))
    with triggered(pattern_prop(DEFAULT_TYPE, gearset.id), value=None), pytest.raises(PreventUpdate):
        callbacks.toggle_default_gearset([None], stored(gearset))


def test_pattern_callbacks_ignore_other_control_types():
    """Ignore a trigger from a different kind of per-row control."""
    gearset = make_gearset()

    with triggered(pattern_prop(DELETE_TYPE, gearset.id)), pytest.raises(PreventUpdate):
        callbacks.select_gearset([1], stored(gearset))


def test_select_gearset_loads_it_as_an_internal_build():
    """Select a gearset by ID and hand its stats to the form via the loaded-build store."""
    first, second = make_gearset("First"), make_gearset("Second", Role.TANK)

    with triggered(pattern_prop(SELECT_TYPE, second.id)):
        selected, build, selector_style = callbacks.select_gearset([None, 1], stored(first, second))

    assert selected == second.id
    assert build["build_provider"] == BuildProvider.INTERNAL
    assert (build["build_name"], build["build_role"]) == ("Second", "Tank")
    assert selector_style == {"display": "none"}


@pytest.mark.parametrize("cell", ["name", "role"], ids=["name-cell", "role-cell"])
def test_select_gearset_from_either_clickable_cell(cell):
    """Load a gearset when any of its row's clickable cells is clicked."""
    gearset = make_gearset("Clicked")

    with triggered(pattern_prop(SELECT_TYPE, gearset.id, cell=cell)):
        selected, build, _ = callbacks.select_gearset([1, None], stored(gearset))

    assert selected == gearset.id
    assert build["build_name"] == "Clicked"


def test_select_gearset_for_missing_gearset_does_nothing():
    """Do nothing when the clicked gearset no longer exists."""
    with triggered(pattern_prop(SELECT_TYPE, "11111111-1111-4111-8111-111111111111")), pytest.raises(PreventUpdate):
        callbacks.select_gearset([1], stored(make_gearset()))


def test_selected_gearset_fills_the_form_through_the_shared_apply_callback():
    """Fill the form from a selected gearset using the existing apply callback."""
    gearset = make_gearset("Tank", Role.TANK, 3)
    build = gearset.to_internal_build().model_dump(mode="json")

    with triggered("loaded-job-build.data", build):
        values = apply_loaded_job_build(build, None)

    assert values[0] == "Tank"
    assert values[1:] == tuple(getattr(gearset.stats, stat.value) for stat in STAT_ORDER)


def test_hidden_xiv_gear_selector_does_not_reapply_a_saved_gearset():
    """Ignore XIVGear selector changes while a saved gearset is loaded."""
    build = make_gearset().to_internal_build().model_dump(mode="json")

    with triggered("xiv-gear-select.value", "1"):
        values = apply_loaded_job_build(build, "1")

    assert values == (no_update,) * 8


@pytest.mark.parametrize(
    ("build", "expected_cleared"),
    [
        (None, True),
        ({"build_provider": "etro.gg"}, True),
        ({"build_provider": "xivgear.app"}, True),
        ({"build_provider": "internal"}, False),
    ],
    ids=["failed-load", "etro", "xivgear", "internal"],
)
def test_provider_builds_clear_the_selected_gearset(build, expected_cleared):
    """Forget the selected gearset only when a provider build replaces it."""
    result = callbacks.clear_selection_for_provider_build(build, None)

    assert (result is None) is expected_cleared
    if not expected_cleared:
        assert result is no_update


def test_toggle_default_sets_then_clears_the_default():
    """Toggle the same gearset between default and not default."""
    first, second = make_gearset("First"), make_gearset("Second")

    with triggered(pattern_prop(DEFAULT_TYPE, second.id)):
        with_default = callbacks.toggle_default_gearset([None, 1], stored(first, second))
        assert library_from_storage(with_default).default_id == second.id

        cleared = callbacks.toggle_default_gearset([None, 1], with_default)
        assert library_from_storage(cleared).default_id is None


def test_toggle_default_moves_the_default_between_gearsets():
    """Move the default when another gearset's star is clicked."""
    first, second = make_gearset("First"), make_gearset("Second")

    with triggered(pattern_prop(DEFAULT_TYPE, first.id)):
        result = callbacks.toggle_default_gearset([1, None], stored(first, second, default=second))

    assert library_from_storage(result).default_id == first.id


def test_toggle_default_for_missing_gearset_does_nothing():
    """Do nothing when the starred gearset no longer exists."""
    with triggered(pattern_prop(DEFAULT_TYPE, "11111111-1111-4111-8111-111111111111")), pytest.raises(PreventUpdate):
        callbacks.toggle_default_gearset([1], stored(make_gearset()))


def test_delete_request_opens_confirmation_naming_the_gearset():
    """Ask for confirmation before deleting, without changing any data yet."""
    gearset = make_gearset("Precious")

    with triggered(pattern_prop(DELETE_TYPE, gearset.id)):
        result = callbacks.delete_gearset_flow([1], None, None, None, None, stored(gearset))

    opened, pending, text, library_data, selected = result
    assert (opened, pending) == (True, gearset.id)
    assert "Precious" in text
    assert (library_data, selected) == (no_update, no_update)


def test_delete_cancel_closes_without_deleting():
    """Close the modal and forget the pending gearset on cancel."""
    gearset = make_gearset()

    with triggered("gearset-delete-cancel.n_clicks"):
        result = callbacks.delete_gearset_flow([None], None, 1, gearset.id, None, stored(gearset))

    assert result == (False, None, no_update, no_update, no_update)


def test_delete_confirm_removes_the_pending_gearset_and_clears_selection():
    """Delete the pending gearset, its default status, and a matching selection."""
    first, second = make_gearset("First"), make_gearset("Second")

    with triggered("gearset-delete-confirm.n_clicks"):
        opened, pending, _, library_data, selected = callbacks.delete_gearset_flow(
            [None, None], 1, None, first.id, first.id, stored(first, second, default=first)
        )

    library = library_from_storage(library_data)
    assert [g.id for g in library.gearsets] == [second.id]
    assert library.default_id is None
    assert (opened, pending, selected) == (False, None, None)


def test_delete_confirm_keeps_selection_of_another_gearset():
    """Leave the selection alone when a different gearset is deleted."""
    first, second = make_gearset("First"), make_gearset("Second")

    with triggered("gearset-delete-confirm.n_clicks"):
        result = callbacks.delete_gearset_flow([None, None], 1, None, first.id, second.id, stored(first, second))

    assert result[4] is no_update


def test_delete_confirm_for_already_deleted_gearset_just_closes():
    """Close quietly if the pending gearset vanished before confirmation."""
    with triggered("gearset-delete-confirm.n_clicks"):
        result = callbacks.delete_gearset_flow(
            [None], 1, None, "11111111-1111-4111-8111-111111111111", None, stored(make_gearset())
        )

    assert result == (False, None, no_update, no_update, no_update)


def test_delete_flow_ignores_rerender_triggers():
    """Ignore zero-click triggers caused by re-rendering the table."""
    gearset = make_gearset()

    with triggered(pattern_prop(DELETE_TYPE, gearset.id), value=0), pytest.raises(PreventUpdate):
        callbacks.delete_gearset_flow([0], None, None, None, None, stored(gearset))
