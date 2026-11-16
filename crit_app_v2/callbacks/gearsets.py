"""Callbacks wiring the saved-gearset manager to the player-analysis form."""

from dash import ALL, Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
from pydantic import ValidationError

from crit_app_v2.build_providers import BuildProvider, validate_job_stats_form
from crit_app_v2.game_data import Role, Stats
from crit_app_v2.gearsets import (
    MAX_GEARSET_NAME_LENGTH,
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    GearsetLibraryError,
    GearsetLimitError,
    SavedGearset,
    library_from_storage,
    library_to_storage,
    migrate_legacy_gearsets,
)
from crit_app_v2.ui.gearset_manager import (
    DEFAULT_TYPE,
    DELETE_TYPE,
    SELECT_TYPE,
    UPDATE_TYPE,
    gearset_table_rows,
    loaded_gearset_badge,
)

_FORM_STATS = (
    Stats.MAIN_STAT,
    Stats.DETERMINATION,
    Stats.SPEED_STAT,
    Stats.CRITICAL_HIT,
    Stats.DIRECT_HIT,
    Stats.WEAPON_DAMAGE,
    Stats.TENACITY,
)
_FORM_STATE = (
    State("role-select", "value"),
    State("main-stat-input", "value"),
    State("determination-stat-input", "value"),
    State("speed-stat-input", "value"),
    State("critical-hit-stat-input", "value"),
    State("direct-hit-stat-input", "value"),
    State("weapon-damage-stat-input", "value"),
    State("tenacity-stat-input", "value"),
)
_INVALID_STATS_MESSAGE = "Enter valid values for every stat before saving."
_LIMIT_MESSAGE = f"You can save up to {MAX_SAVED_GEARSETS} gearsets. Delete one first."
_MISSING_MESSAGE = "That gearset no longer exists."


def _library(data: object) -> GearsetLibrary:
    """Read stored library data, treating missing or invalid data as empty.

    Parameters
    ----------
    data
        Value of the ``gearset-library`` store.

    Returns
    -------
    GearsetLibrary
        The stored library, or an empty one.
    """
    return library_from_storage(data) or GearsetLibrary()


def _form_stats(values: tuple[int | None, ...]) -> dict[Stats, int | None]:
    """Key positional form values by statistic.

    Parameters
    ----------
    values
        Stat values in ``_FORM_STATS`` order.

    Returns
    -------
    dict[Stats, int | None]
        Values keyed by statistic.
    """
    return dict(zip(_FORM_STATS, values, strict=True))


def _clicked_gearset_id(component_type: str) -> str | None:
    """Return the gearset ID of a genuinely clicked per-gearset control.

    Re-rendering the table recreates its buttons with zero clicks and fires the
    pattern-matching callbacks; those triggers are ignored here.

    Parameters
    ----------
    component_type
        Pattern-matching type of the control that should have been clicked.

    Returns
    -------
    str | None
        The gearset ID, or ``None`` if the trigger was not a real click.
    """
    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict) or triggered_id.get("type") != component_type:
        return None
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return None
    return triggered_id.get("gearset_id")


def _persist(library: GearsetLibrary) -> dict[str, object]:
    """Serialize a library for the ``gearset-library`` store."""
    return library_to_storage(library)


@callback(
    Output("gearset-library", "data"),
    Output("selected-gearset-id", "data"),
    Output("loaded-job-build", "data", allow_duplicate=True),
    Input("gearset-apply-default", "data"),
    State("gearset-library", "data"),
    State("saved-gearsets", "data"),
    State("default-gear-index", "data"),
    prevent_initial_call="initial_duplicate",
)
def initialize_gearsets(
    apply_default: bool,
    stored_library: object,
    legacy_gearsets: object,
    legacy_default_index: object,
):
    """Migrate legacy gearsets once and load the default into the form.

    The default is only applied when ``apply_default`` is true, so a saved
    analysis never has its stats overwritten.
    """
    library = library_from_storage(stored_library)
    library_output = no_update
    if library is None:
        library = migrate_legacy_gearsets(legacy_gearsets, legacy_default_index).library
        library_output = _persist(library)

    default = library.default_gearset if apply_default else None
    if default is None:
        return library_output, no_update, no_update
    return (
        library_output,
        default.id,
        default.to_internal_build().model_dump(mode="json"),
    )


@callback(
    Output("gearset-table-body", "children"),
    Output("loaded-gearset-badge", "children"),
    Input("gearset-library", "data"),
    Input("selected-gearset-id", "data"),
)
def render_gearsets(stored_library: object, selected_id: str | None):
    """Render the gearset table and the badge naming the loaded gearset."""
    library = _library(stored_library)
    return (
        gearset_table_rows(library, selected_id),
        loaded_gearset_badge(library, selected_id),
    )


@callback(
    Output("save-gearset-button", "disabled"),
    Input("new-gearset-name", "value"),
    Input("role-select", "value"),
    Input("main-stat-input", "value"),
    Input("determination-stat-input", "value"),
    Input("speed-stat-input", "value"),
    Input("critical-hit-stat-input", "value"),
    Input("direct-hit-stat-input", "value"),
    Input("weapon-damage-stat-input", "value"),
    Input("tenacity-stat-input", "value"),
    Input("gearset-library", "data"),
)
def enable_save_new_gearset(name: str | None, role: str, *values):
    """Enable "Save as new set" for a named, valid form with room to spare."""
    *stat_values, stored_library = values
    if not name or not name.strip() or len(name.strip()) > MAX_GEARSET_NAME_LENGTH:
        return True
    if len(_library(stored_library).gearsets) >= MAX_SAVED_GEARSETS:
        return True
    return not validate_job_stats_form(
        Role(role), _form_stats(tuple(stat_values))
    ).is_valid


@callback(
    Output("gearset-library", "data", allow_duplicate=True),
    Output("selected-gearset-id", "data", allow_duplicate=True),
    Output("new-gearset-name", "value"),
    Output("gearset-message", "children"),
    Input("save-gearset-button", "n_clicks"),
    State("new-gearset-name", "value"),
    *_FORM_STATE,
    State("gearset-library", "data"),
    prevent_initial_call=True,
)
def save_new_gearset(n_clicks: int | None, name: str | None, role: str, *values):
    """Save the form's stats as a new gearset and select it."""
    if not n_clicks:
        raise PreventUpdate
    *stat_values, stored_library = values
    try:
        gearset = SavedGearset.from_form_values(
            name, Role(role), _form_stats(tuple(stat_values))
        )
        library = _library(stored_library).add(gearset)
    except ValidationError:
        return no_update, no_update, no_update, _INVALID_STATS_MESSAGE
    except GearsetLimitError:
        return no_update, no_update, no_update, _LIMIT_MESSAGE
    return _persist(library), gearset.id, "", None


@callback(
    Output("gearset-library", "data", allow_duplicate=True),
    Output("selected-gearset-id", "data", allow_duplicate=True),
    Output("gearset-message", "children", allow_duplicate=True),
    Input({"type": UPDATE_TYPE, "gearset_id": ALL}, "n_clicks"),
    *_FORM_STATE,
    State("gearset-library", "data"),
    prevent_initial_call=True,
)
def update_gearset(_n_clicks: list[int | None], role: str, *values):
    """Overwrite a saved gearset's role and stats with the form's values."""
    gearset_id = _clicked_gearset_id(UPDATE_TYPE)
    if gearset_id is None:
        raise PreventUpdate
    *stat_values, stored_library = values
    library = _library(stored_library)
    existing = library.get(gearset_id)
    if existing is None:
        return no_update, no_update, _MISSING_MESSAGE
    try:
        updated = SavedGearset.from_form_values(
            existing.name,
            Role(role),
            _form_stats(tuple(stat_values)),
            gearset_id=existing.id,
        )
    except ValidationError:
        return no_update, no_update, _INVALID_STATS_MESSAGE
    return _persist(library.replace(updated)), updated.id, None


@callback(
    Output("selected-gearset-id", "data", allow_duplicate=True),
    Output("loaded-job-build", "data", allow_duplicate=True),
    Output("xiv-gear-select", "style", allow_duplicate=True),
    Input({"type": SELECT_TYPE, "gearset_id": ALL}, "n_clicks", partial_pattern=True),
    State("gearset-library", "data"),
    prevent_initial_call=True,
)
def select_gearset(_n_clicks: list[int | None], stored_library: object):
    """Load a clicked gearset into the form via the shared loaded-build store."""
    gearset_id = _clicked_gearset_id(SELECT_TYPE)
    gearset = _library(stored_library).get(gearset_id)
    if gearset is None:
        raise PreventUpdate
    return (
        gearset.id,
        gearset.to_internal_build().model_dump(mode="json"),
        {"display": "none"},
    )


@callback(
    Output("selected-gearset-id", "data", allow_duplicate=True),
    Input("loaded-job-build", "data"),
    Input("xiv-gear-select", "value"),
    prevent_initial_call=True,
)
def clear_selection_for_provider_build(
    build_data: dict[str, object] | None, _sheet_index
):
    """Forget the selected gearset once a provider build takes over the form."""
    if build_data and build_data.get("build_provider") == BuildProvider.INTERNAL:
        return no_update
    return None


@callback(
    Output("gearset-library", "data", allow_duplicate=True),
    Input({"type": DEFAULT_TYPE, "gearset_id": ALL}, "n_clicks"),
    State("gearset-library", "data"),
    prevent_initial_call=True,
)
def toggle_default_gearset(_n_clicks: list[int | None], stored_library: object):
    """Make a gearset the default, or clear it if it already is."""
    gearset_id = _clicked_gearset_id(DEFAULT_TYPE)
    if gearset_id is None:
        raise PreventUpdate
    library = _library(stored_library)
    try:
        new_default = None if library.default_id == gearset_id else gearset_id
        return _persist(library.with_default(new_default))
    except GearsetLibraryError:
        raise PreventUpdate


@callback(
    Output("gearset-delete-modal", "opened"),
    Output("gearset-pending-delete", "data"),
    Output("gearset-delete-text", "children"),
    Output("gearset-library", "data", allow_duplicate=True),
    Output("selected-gearset-id", "data", allow_duplicate=True),
    Input({"type": DELETE_TYPE, "gearset_id": ALL}, "n_clicks"),
    Input("gearset-delete-confirm", "n_clicks"),
    Input("gearset-delete-cancel", "n_clicks"),
    State("gearset-pending-delete", "data"),
    State("selected-gearset-id", "data"),
    State("gearset-library", "data"),
    prevent_initial_call=True,
)
def delete_gearset_flow(
    _delete_clicks: list[int | None],
    confirm_clicks: int | None,
    cancel_clicks: int | None,
    pending_id: str | None,
    selected_id: str | None,
    stored_library: object,
):
    """Ask for confirmation, then delete the pending gearset."""
    library = _library(stored_library)
    close = (False, None, no_update, no_update, no_update)

    requested_id = _clicked_gearset_id(DELETE_TYPE)
    if requested_id is not None:
        gearset = library.get(requested_id)
        if gearset is None:
            raise PreventUpdate
        text = f'Delete "{gearset.name}"? This cannot be undone.'
        return True, requested_id, text, no_update, no_update

    if ctx.triggered_id == "gearset-delete-cancel" and cancel_clicks:
        return close
    if ctx.triggered_id == "gearset-delete-confirm" and confirm_clicks:
        if pending_id is None or library.get(pending_id) is None:
            return close
        new_selected = None if selected_id == pending_id else no_update
        return (
            False,
            None,
            no_update,
            _persist(library.remove(pending_id)),
            new_selected,
        )
    raise PreventUpdate
