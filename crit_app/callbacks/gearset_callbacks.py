"""
This module contains all callback functions related to gearset management.

for the How Bad Was My Crit In XIV application.
"""

import json

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Input, Output, State, callback, ctx, html
from dash.exceptions import PreventUpdate

from crit_app.job_data.encounter_data import stat_ranges
from crit_app.shared_elements import validate_meldable_stat
from crit_app.util.gearset_manager import (
    create_gearset_selector_options,
    is_valid_gearset_index,
    set_is_selected_fields,
)

# Define commonly used return values
valid_stat_return = (True, False)
invalid_stat_return = (False, True)


@callback(
    Output("TEN", "valid"),
    Output("TEN", "invalid"),
    Input("TEN", "value"),
    Input("role-select", "value"),
)
def valid_tenacity(tenacity: int, role: str) -> tuple:
    """
    Validate the tenacity stat input.

    Parameters:
    tenacity (int): The value of the tenacity stat to validate.
    role (str): The selected role.

    Returns:
    tuple: A tuple containing the validation results for the tenacity stat.
    """
    if role != "Tank":
        return valid_stat_return

    if tenacity is None:
        return invalid_stat_return

    if validate_meldable_stat(
        "test",
        tenacity,
        stat_ranges["TEN"]["lower"],
        stat_ranges["TEN"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(
    Output("gearset-table-body", "children"),
    Input("saved-gearsets", "data"),
    Input("default-gear-index", "data"),  # Add input for default index
)
def populate_gearset_table(gearsets_data, default_gear_index):
    """Populate the gearset management table with data from local storage."""
    tbody_rows = []

    # Convert default_gear_index to int if possible
    try:
        default_gear_index = (
            int(default_gear_index) if default_gear_index is not None else None
        )
    except (ValueError, TypeError):
        default_gear_index = None

    # Add existing gearset rows if any exist
    if gearsets_data:
        for i, gearset in enumerate(gearsets_data):
            # Determine row style based on whether it's the default
            row_style = (
                {"backgroundColor": "rgba(0, 123, 255, 0.3)"}
                if i == default_gear_index
                else {}
            )
            row_style["cursor"] = "pointer"  # Keep the cursor style
            default_append = " (Default)" if i == default_gear_index else ""
            tbody_rows.append(
                html.Tr(
                    [
                        html.Td(
                            dbc.RadioButton(
                                id={"type": "gearset-select", "index": i},
                                className="gearset-select",
                                value=gearset.get(
                                    "is_selected", False
                                ),  # Use .get with default
                                name="gearset-select-group",
                            )
                        ),
                        html.Td(gearset.get("role", "")),
                        html.Td(
                            gearset.get("name", "") + default_append,
                            style={"whiteSpace": "normal", "wordWrap": "break-word"},
                        ),
                        # Update button column
                        html.Td(
                            html.Div(
                                dbc.Button(
                                    html.I(className="fas fa-sync-alt"),
                                    id={"type": "gearset-update", "index": i},
                                    color="link",  # Revert back to link
                                    className="gearset-update-button",  # Keep specific class
                                    size="sm",
                                ),
                            )
                        ),
                        # Delete button column
                        html.Td(
                            html.Div(
                                dbc.Button(
                                    html.I(className="fas fa-trash"),
                                    id={"type": "gearset-delete", "index": i},
                                    color="link",
                                    className="text-danger gearset-delete-button",  # Add class here
                                    size="sm",
                                ),
                            )
                        ),
                    ],
                    id={"type": "gearset-row", "index": i},
                    className="gearset-row",
                    style=row_style,  # Apply conditional style here
                )
            )

    # Add save button row
    tbody_rows.append(
        html.Tr(
            [
                html.Td(""),
                html.Td(
                    dbc.Button(
                        [html.I(className="fas fa-plus me-2"), " New set"],
                        id="save-gearset-button",
                        color="primary",
                        size="sm",
                        disabled=True,
                    )
                ),
                html.Td(
                    dbc.Input(
                        id="new-gearset-name",
                        placeholder="Enter gearset name",
                        type="text",
                    )
                ),
                html.Td(""),
                html.Td(""),
            ]
        )
    )

    return tbody_rows


@callback(
    Output("saved-gearsets", "data", allow_duplicate=True),
    Output("default-set-selector", "options", allow_duplicate=True),
    Input({"type": "gearset-update", "index": ALL}, "n_clicks"),
    State("saved-gearsets", "data"),
    State("role-select", "value"),
    State("main-stat", "value"),
    State("TEN", "value"),
    State("DET", "value"),
    State("speed-stat", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    prevent_initial_call=True,
)
def update_gearset(
    n_clicks_list,
    saved_gearsets,
    role,
    main_stat,
    tenacity,
    determination,
    speed,
    crit,
    direct_hit,
    weapon_damage,
):
    """Update an existing gearset with current stat values."""
    triggered = ctx.triggered_id
    no_clicks = not any(n_clicks_list)
    if not triggered or no_clicks:
        raise PreventUpdate

    # Check if the triggered input is one of the update buttons and has been clicked
    if isinstance(triggered, dict) and triggered.get("type") == "gearset-update":
        try:
            idx = triggered.get("index")
            # Find the corresponding n_clicks value from the input list
            trigger_index_in_list = -1
            for i, item in enumerate(ctx.inputs_list[0]):
                if item["id"] == triggered:
                    trigger_index_in_list = i
                    break

            # Ensure the button was actually clicked (n_clicks is not None and > 0)
            if (
                idx is not None
                and trigger_index_in_list != -1
                and n_clicks_list[trigger_index_in_list]
            ):
                # Check if the index is valid using the helper function
                if is_valid_gearset_index(idx, saved_gearsets):
                    # Get the existing gearset name
                    existing_name = saved_gearsets[idx].get("name", "Unnamed")
                    # Preserve any special properties the gearset might have had
                    is_selected = True

                    # Update the gearset with current values
                    updated_gearset = {
                        "role": role,
                        "name": existing_name,
                        "main_stat": main_stat,
                        "determination": determination,
                        "speed": speed,
                        "crit": crit,
                        "direct_hit": direct_hit,
                        "weapon_damage": weapon_damage,
                        "is_selected": is_selected,
                    }

                    # Add tenacity for tanks
                    if role == "Tank" and tenacity is not None:
                        updated_gearset["tenacity"] = tenacity

                    # Update the gearset in the list
                    saved_gearsets[idx] = updated_gearset
                    saved_gearsets = set_is_selected_fields(saved_gearsets, idx)
                    # Update selector options using the helper function
                    selector_options = create_gearset_selector_options(saved_gearsets)

                    return saved_gearsets, selector_options

                else:
                    # Index out of bounds
                    raise PreventUpdate
            else:
                # Triggered but n_clicks is None or 0
                raise PreventUpdate

        except Exception as e:
            # Log the error for debugging
            print(f"Error updating gearset: {e}")
            raise PreventUpdate
    else:
        # Triggered by something else
        raise PreventUpdate


@callback(
    Output("save-gearset-button", "disabled"),
    Input("role-select", "value"),
    Input("new-gearset-name", "value"),
    Input("main-stat", "valid"),
    Input("TEN", "valid"),
    Input("DET", "valid"),
    Input("speed-stat", "valid"),
    Input("CRT", "valid"),
    Input("DH", "valid"),
    Input("WD", "valid"),
    State("saved-gearsets", "data"),
)
def validate_save_new_gearset(
    role,
    gearset_name,
    main_stat_valid,
    ten_valid,
    det_valid,
    speed_valid,
    crt_valid,
    dh_valid,
    wd_valid,
    saved_gearsets,
):
    """
    Validate if all required gearset inputs are valid and count is below limit.

    to enable the Save New Set button.

    Parameters:
    role (str): The selected role
    gearset_name (str): Name for the gearset
    main_stat_valid (bool): Whether main stat is valid
    ten_valid (bool): Whether tenacity is valid
    det_valid (bool): Whether determination is valid
    speed_valid (bool): Whether speed stat is valid
    crt_valid (bool): Whether critical hit is valid
    dh_valid (bool): Whether direct hit is valid
    wd_valid (bool): Whether weapon damage is valid
    saved_gearsets (list): The current list of saved gearsets

    Returns:
    bool: True if button should be disabled, False otherwise
    """
    # Check gearset count limit
    if saved_gearsets and len(saved_gearsets) >= 25:
        return True  # Disable if 25 or more gearsets exist

    # Check if name is provided
    if not gearset_name or len(gearset_name.strip()) == 0:
        return True

    # Check if role is selected
    if not role or role == "Unsupported":
        return True

    # If Tank, all stats must be valid including TEN
    if role == "Tank":
        return not all(
            [
                main_stat_valid,
                ten_valid,
                det_valid,
                speed_valid,
                crt_valid,
                dh_valid,
                wd_valid,
            ]
        )

    # For non-tanks, all stats except TEN must be valid
    return not all(
        [main_stat_valid, det_valid, speed_valid, crt_valid, dh_valid, wd_valid]
    )


@callback(
    Output("role-select", "value"),
    Output("main-stat", "value"),
    Output("DET", "value"),
    Output("speed-stat", "value"),
    Output("CRT", "value"),
    Output("DH", "value"),
    Output("WD", "value"),
    Output("TEN", "value"),
    Output("job-build-name-div", "children"),
    Output("default-set-selector", "options"),
    Output("saved-gearsets", "data"),
    Output("default-set-selector", "value"),
    Input("analysis-indicator", "data"),
    State("default-gear-index", "data"),
    State("saved-gearsets", "data"),
    State("role-select", "value"),
    State("main-stat", "value"),
    State("DET", "value"),
    State("speed-stat", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    State("TEN", "value"),
)
def load_default_gearset(
    analysis_indicator,
    default_gear_index,
    saved_gearsets,
    current_role,
    current_main_stat,
    current_det,
    current_speed,
    current_crit,
    current_dh,
    current_wd,
    current_ten,
):
    """
    Load default gearset info and conditionally apply default stats.

    Only applies default stat values when creating a new analysis.
    Always loads default set name and selector options/value.
    """
    no_update_stats = [
        current_role,
        current_main_stat,
        current_det,
        current_speed,
        current_crit,
        current_dh,
        current_wd,
        current_ten,
    ]

    empty_job_build_name = []
    empty_options = create_gearset_selector_options([])
    no_default_value = "-1"  # Value representing no default

    # no gearsets saved, do not load anything
    if not saved_gearsets:
        # No gearsets saved, return empty default info
        saved_gearsets = set_is_selected_fields(saved_gearsets, -1)

        return tuple(
            no_update_stats
            + [
                empty_job_build_name,
                empty_options,
                saved_gearsets,
                no_default_value,  # Set dropdown value to "No Default"
            ]
        )

    #### Manage gearset selector options ####
    # Prepare selector options (always needed) using the helper function
    selector_options = create_gearset_selector_options(saved_gearsets)

    # Handle type conversion for default_gear_index
    try:
        # Convert to int if it's a string or keep as is if already an int or None
        default_gear_index = (
            int(default_gear_index) if default_gear_index not in (None, "") else None
        )
    except (ValueError, TypeError):
        default_gear_index = None

    # Use helper function for validation
    invalid_default_gearset_index = not is_valid_gearset_index(
        default_gear_index, saved_gearsets
    )

    # Handle invalid default index
    if invalid_default_gearset_index:
        # No selection
        saved_gearsets = set_is_selected_fields(saved_gearsets, -1)
        # Set dropdown value to "No Default"
        dropdown_value = no_default_value
        # Return current values, which includes an empty gearset
        return tuple(
            no_update_stats
            + [
                empty_job_build_name,
                selector_options,
                saved_gearsets,
                dropdown_value,
            ]
        )

    # We have a valid default gearset
    default_gearset = saved_gearsets[default_gear_index]
    default_name = default_gearset.get("name", "Unnamed")

    job_build_name = []
    # Set dropdown value to the default index (as string)
    dropdown_value = str(default_gear_index)

    if analysis_indicator:
        # No selection
        saved_gearsets = set_is_selected_fields(saved_gearsets, -1)

        # For an existing analysis, don't load default stat values
        return tuple(
            no_update_stats
            + [
                empty_job_build_name,
                selector_options,
                saved_gearsets,
                dropdown_value,
            ]
        )
    else:
        # For a new analysis, load the default values
        job_build_name = [html.H4(f"Build name: {default_name}")]
        # Update selected gearset
        saved_gearsets = set_is_selected_fields(saved_gearsets, default_gear_index)

        return (
            default_gearset.get("role", "Healer"),
            default_gearset.get("main_stat", None),
            default_gearset.get("determination", None),
            default_gearset.get("speed", None),
            default_gearset.get("crit", None),
            default_gearset.get("direct_hit", None),
            default_gearset.get("weapon_damage", None),
            default_gearset.get("tenacity", None),
            job_build_name,
            selector_options,
            saved_gearsets,
            dropdown_value,  # Keep dropdown value reflecting the default
        )


@callback(
    Output("default-gear-index", "data"),
    Input("default-set-selector", "value"),
    State("saved-gearsets", "data"),
    prevent_initial_call=True,
)
def set_default_gearset(selected_value, saved_gearsets):
    """Set the selected gearset as the default gearset based on dropdown value."""
    # selected_value is now the string index or "-1" for "No Default"
    if selected_value is None:
        # This might happen if options change and value becomes invalid
        # Treat as "No Default"
        return None

    # Handle "No Default" selection
    if selected_value == "-1":
        return None

    # Validate the selected index using helper function
    try:
        selected_index = int(selected_value)

        if not is_valid_gearset_index(selected_index, saved_gearsets):
            # This case might happen if data is out of sync, revert to no default
            return None

        # Return updated info with selected_index (as int) going to default-gear-index
        return selected_index

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


@callback(
    Output({"type": "gearset-select", "index": MATCH}, "value"),
    Input({"type": "gearset-row", "index": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def handle_row_click(n_clicks):
    """
    Handle clicks on gearset rows to select the gearset.

    Prevents selection when clicking delete or update buttons.
    """
    if n_clicks is None:
        raise PreventUpdate

    # Check if click was on a button or icon by examining className in event target
    if hasattr(ctx, "triggered_submit_button"):
        element = ctx.triggered_submit_button
        if element and isinstance(element, dict):
            class_name = element.get("className", "")
            if "fas fa-trash" in class_name or "fas fa-sync-alt" in class_name:
                raise PreventUpdate

    # If we get here, it was a legitimate row click
    return True


@callback(
    Output("saved-gearsets", "data", allow_duplicate=True),
    Output("default-set-selector", "options", allow_duplicate=True),
    Input("save-gearset-button", "n_clicks"),
    State("role-select", "value"),
    State("new-gearset-name", "value"),
    State("main-stat", "value"),
    State("TEN", "value"),
    State("DET", "value"),
    State("speed-stat", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    State("saved-gearsets", "data"),
    prevent_initial_call=True,
)
def save_new_gearset(
    n_clicks,
    role,
    gearset_name,
    main_stat,
    tenacity,
    determination,
    speed,
    crit,
    direct_hit,
    weapon_damage,
    saved_gearsets,
):
    """Save a new gearset to local storage."""
    if n_clicks is None:
        raise PreventUpdate

    # Create new gearset record
    new_gearset = {
        "role": role,
        "name": gearset_name,
        "main_stat": main_stat,
        "determination": determination,
        "speed": speed,
        "crit": crit,
        "direct_hit": direct_hit,
        "weapon_damage": weapon_damage,
        "is_selected": True,
    }

    # Add tenacity for tanks
    if role == "Tank" and tenacity is not None:
        new_gearset["tenacity"] = tenacity

    # Initialize saved_gearsets if it's None or not a list
    if saved_gearsets is None or not isinstance(saved_gearsets, list):
        saved_gearsets = []

    # Append the new gearset to saved_gearsets
    saved_gearsets.append(new_gearset)

    # Select the newly made set.
    saved_gearsets = set_is_selected_fields(saved_gearsets, len(saved_gearsets) - 1)
    # Update the selector options using helper function
    selector_options = create_gearset_selector_options(saved_gearsets)

    # Return updated gearsets and clear the name input field
    return saved_gearsets, selector_options


@callback(
    Output("role-select", "value", allow_duplicate=True),
    Output("main-stat", "value", allow_duplicate=True),
    Output("DET", "value", allow_duplicate=True),
    Output("speed-stat", "value", allow_duplicate=True),
    Output("CRT", "value", allow_duplicate=True),
    Output("DH", "value", allow_duplicate=True),
    Output("WD", "value", allow_duplicate=True),
    Output("TEN", "value", allow_duplicate=True),
    Output("job-build-name-div", "children", allow_duplicate=True),
    Input({"type": "gearset-select", "index": ALL}, "value"),
    State({"type": "gearset-select", "index": ALL}, "id"),
    State("saved-gearsets", "data"),
    prevent_initial_call=True,
)
def load_selected_gearset(radio_values, radio_ids, saved_gearsets):
    """Load the selected gearset data into the form fields when a radio button is selected."""
    # Get the triggered component
    triggered = ctx.triggered[0] if ctx.triggered else None
    if triggered is None:
        raise PreventUpdate

    # Parse the triggered component's property ID to get index
    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        triggered_index = triggered_id["index"]

        # Only proceed if this radio button was just selected (turned ON)
        if not triggered["value"]:
            raise PreventUpdate
    except Exception:
        # Fall back to scanning all radio values
        selected_index = None
        for i, val in enumerate(radio_values):
            if val and i < len(radio_ids):
                selected_index = radio_ids[i]["index"]
                break

        # If no radio is selected, do nothing
        if selected_index is None:
            raise PreventUpdate

        triggered_index = selected_index

    if not saved_gearsets or triggered_index >= len(saved_gearsets):
        raise PreventUpdate

    # Get the selected gearset
    selected_gearset = saved_gearsets[triggered_index]

    # Create job build name div content
    job_build_name_div = [
        html.H4(f"Build name: {selected_gearset.get('name', 'Untitled')}")
    ]

    # Return values to fill in the form fields
    return (
        selected_gearset.get("role", ""),
        selected_gearset.get("main_stat", None),
        selected_gearset.get("determination", None),
        selected_gearset.get("speed", None),
        selected_gearset.get("crit", None),
        selected_gearset.get("direct_hit", None),
        selected_gearset.get("weapon_damage", None),
        selected_gearset.get("tenacity", None),
        job_build_name_div,
    )


@callback(
    Output("saved-gearsets", "data", allow_duplicate=True),
    Output("default-gear-index", "data", allow_duplicate=True),
    Output("default-set-selector", "options", allow_duplicate=True),
    Output(
        "default-set-selector", "value", allow_duplicate=True
    ),  # Add output for dropdown value
    Input({"type": "gearset-delete", "index": ALL}, "n_clicks"),
    State("saved-gearsets", "data"),
    State("default-gear-index", "data"),
    prevent_initial_call=True,
)
def delete_gearset(n_clicks_list, saved_gearsets, default_gear_index):
    """Delete a gearset when its trash icon is clicked and update default gearset if needed."""
    triggered = ctx.triggered_id
    no_clicks = not any(n_clicks_list)
    if not triggered or no_clicks:
        raise PreventUpdate

    # Check if the triggered input is one of the delete buttons and has been clicked
    if isinstance(triggered, dict) and triggered.get("type") == "gearset-delete":
        try:
            index_to_delete = triggered.get("index")
            # Find the corresponding n_clicks value from the input list
            trigger_index_in_list = -1
            for i, item in enumerate(ctx.inputs_list[0]):
                if item["id"] == triggered:
                    trigger_index_in_list = i
                    break

            # Ensure the button was actually clicked (n_clicks is not None and > 0)
            if (
                index_to_delete is not None
                and trigger_index_in_list != -1
                and n_clicks_list[trigger_index_in_list]
            ):
                # Check if the index is valid using helper function
                if is_valid_gearset_index(index_to_delete, saved_gearsets):
                    # Check if we're deleting the default gearset
                    # Ensure default_gear_index is an int for comparison, handle None
                    try:
                        current_default_idx = (
                            int(default_gear_index)
                            if default_gear_index is not None
                            else None
                        )
                    except (ValueError, TypeError):
                        current_default_idx = None

                    is_deleting_default = current_default_idx == index_to_delete

                    # Remove the gearset at the specified index
                    del saved_gearsets[index_to_delete]

                    # Update the default gear index if needed
                    new_default_gear_index = current_default_idx
                    dropdown_value = "-1"  # Default to "No Default"

                    if is_deleting_default:
                        # If we deleted the default, reset it
                        new_default_gear_index = None
                        dropdown_value = "-1"
                    elif (
                        current_default_idx is not None
                        and index_to_delete < current_default_idx
                    ):
                        # If we deleted a gearset before the default, decrement the default index
                        new_default_gear_index = current_default_idx - 1
                        # Get updated default display text if there is a default
                        if is_valid_gearset_index(
                            new_default_gear_index, saved_gearsets
                        ):
                            dropdown_value = str(
                                new_default_gear_index
                            )  # Update dropdown value
                        else:
                            # This case should ideally not happen if logic is correct
                            new_default_gear_index = None
                            dropdown_value = "-1"
                    else:
                        # Default stays the same or was None, update display and dropdown value if valid
                        if is_valid_gearset_index(
                            new_default_gear_index, saved_gearsets
                        ):
                            dropdown_value = str(
                                new_default_gear_index
                            )  # Update dropdown value
                        else:
                            # Ensure index is None if it points outside bounds or was None
                            new_default_gear_index = None
                            dropdown_value = "-1"

                    # Update selector options using helper function
                    selector_options = create_gearset_selector_options(saved_gearsets)

                    return (
                        saved_gearsets,
                        new_default_gear_index,
                        selector_options,
                        dropdown_value,
                    )
                else:
                    # Index out of bounds, should not happen with proper UI sync
                    print(
                        f"Warning: Delete index {index_to_delete} out of bounds for saved_gearsets."
                    )
                    raise PreventUpdate
            else:
                # Triggered but n_clicks is None or 0, likely initial load or state issue
                raise PreventUpdate

        except Exception as e:
            print(f"Error deleting gearset: {e}")
            raise PreventUpdate
    else:
        # Triggered by something else (shouldn't happen with this callback structure)
        raise PreventUpdate
