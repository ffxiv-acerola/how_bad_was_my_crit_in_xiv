"""Tests for the saved-gearset manager components."""

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from crit_app_v2.game_data import STAT_INPUTS, Role, Stats
from crit_app_v2.gearsets import GearsetLibrary, SavedGearset
from crit_app_v2.ui.gearset_manager import (
    DEFAULT_ICON,
    DEFAULT_SET_ICON,
    DEFAULT_TYPE,
    DELETE_TYPE,
    LOADED_ICON,
    SELECT_TYPE,
    UPDATE_TYPE,
    gearset_manager,
    gearset_pattern_id,
    gearset_table_rows,
    loaded_gearset_badge,
)


def _library() -> GearsetLibrary:
    """Create a two-gearset library whose second gearset is the default."""
    stats = {stat: STAT_INPUTS[stat].lower for stat in Stats}
    first = SavedGearset.from_form_values("First", Role.TANK, stats)
    second = SavedGearset.from_form_values("Second", Role.HEALER, stats)
    return GearsetLibrary(gearsets=(first, second), default_id=second.id)


def _ids(component) -> list:
    """Collect every component ID beneath a component."""
    return [item.id for item in component._traverse() if getattr(item, "id", None) is not None]


def test_empty_library_renders_a_placeholder_row():
    """Explain that nothing is saved instead of rendering an empty table."""
    rows = gearset_table_rows(GearsetLibrary(), None)

    assert len(rows) == 1
    assert "No saved gearsets" in rows[0].children.children.children


def test_each_gearset_gets_pattern_ids_for_every_action():
    """Key every per-row control by the gearset's ID, not its position."""
    library = _library()
    rows = gearset_table_rows(library, None)

    for gearset, row in zip(library.gearsets, rows, strict=True):
        ids = _ids(row)
        for component_type in (UPDATE_TYPE, DELETE_TYPE, DEFAULT_TYPE):
            assert gearset_pattern_id(component_type, gearset.id) in ids


def test_name_and_role_cells_both_select_the_gearset():
    """Make the name and role cells full-size select buttons, so the row is clickable."""
    library = _library()
    rows = gearset_table_rows(library, None)

    for gearset, row in zip(library.gearsets, rows, strict=True):
        ids = _ids(row)
        assert gearset_pattern_id(SELECT_TYPE, gearset.id, "name") in ids
        assert gearset_pattern_id(SELECT_TYPE, gearset.id, "role") in ids
        buttons = [item for item in row._traverse() if isinstance(item, dmc.UnstyledButton)]
        assert len(buttons) == 2
        assert all(f"Load {gearset.name}" in getattr(button, "aria-label") for button in buttons)


def test_only_the_name_cell_is_a_tab_stop():
    """Avoid two tab stops per row for the same action."""
    row = gearset_table_rows(_library(), None)[0]

    tab_indexes = {item.id["cell"]: item.tabIndex for item in row._traverse() if isinstance(item, dmc.UnstyledButton)}

    assert tab_indexes == {"name": 0, "role": -1}


def test_only_the_selected_row_is_highlighted():
    """Highlight just the gearset loaded into the form."""
    library = _library()
    rows = gearset_table_rows(library, library.gearsets[0].id)

    assert getattr(rows[0], "bg", None) is not None
    assert getattr(rows[1], "bg", None) is None
    assert "bg" not in rows[1].to_plotly_json()["props"]


def test_default_gearset_is_marked():
    """Show a badge and a filled star for the default gearset only."""
    rows = gearset_table_rows(_library(), None)

    def badges(row):
        return [item for item in row._traverse() if isinstance(item, dmc.Badge)]

    def star(row):
        icons = [
            item.icon
            for item in row._traverse()
            if isinstance(item, DashIconify) and item.icon in (DEFAULT_ICON, DEFAULT_SET_ICON)
        ]
        return icons[0]

    assert badges(rows[0]) == [] and star(rows[0]) == DEFAULT_ICON
    assert len(badges(rows[1])) == 1 and star(rows[1]) == DEFAULT_SET_ICON


def test_loaded_badge_names_the_selected_gearset():
    """Show a badge with the loaded gearset's name, and nothing when none is loaded."""
    library = _library()

    badge = loaded_gearset_badge(library, library.gearsets[0].id)

    assert isinstance(badge.children, dmc.Badge)
    assert badge.children.children == "First"
    assert loaded_gearset_badge(library, None) is None
    assert loaded_gearset_badge(library, "11111111-1111-4111-8111-111111111111") is None


def test_only_the_loaded_row_shows_a_check():
    """Mark just the loaded row with a check icon."""
    library = _library()
    rows = gearset_table_rows(library, library.gearsets[0].id)

    def icons(row):
        return [item.icon for item in row._traverse() if isinstance(item, DashIconify)]

    assert LOADED_ICON in icons(rows[0])
    assert LOADED_ICON not in icons(rows[1])


def test_manager_includes_stores_and_modal_with_unique_ids():
    """Provide every ID the callbacks use, without duplicates."""
    ids = _ids(gearset_manager())

    assert len(ids) == len(set(map(str, ids)))
    for expected in (
        "gearset-library",
        "saved-gearsets",
        "default-gear-index",
        "selected-gearset-id",
        "gearset-pending-delete",
        "gearset-apply-default",
        "gearset-table-body",
        "save-gearset-button",
        "new-gearset-name",
        "gearset-delete-modal",
        "gearset-delete-confirm",
        "gearset-delete-cancel",
    ):
        assert expected in ids


def test_manager_stores_use_legacy_keys_in_local_storage():
    """Read the legacy app's storage keys so saved gearsets can be migrated."""
    stores = {
        item.id: item
        for item in gearset_manager()._traverse()
        if getattr(item, "id", None) in {"gearset-library", "saved-gearsets", "default-gear-index"}
    }

    assert {store.storage_type for store in stores.values()} == {"local"}
    assert set(stores) == {"gearset-library", "saved-gearsets", "default-gear-index"}


def test_apply_default_flag_is_stored_for_callbacks():
    """Pass the apply-default choice to the initialization callback."""

    def flag(apply_default):
        return next(
            item.data
            for item in gearset_manager(apply_default)._traverse()
            if getattr(item, "id", None) == "gearset-apply-default"
        )

    assert flag(True) is True
    assert flag(False) is False
