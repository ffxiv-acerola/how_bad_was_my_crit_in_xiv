"""Dash Mantine components for managing saved gearsets."""

from typing import Any

import dash_mantine_components as dmc
from dash import dcc
from dash_iconify import DashIconify

from crit_app_v2.gearsets import (
    MAX_GEARSET_NAME_LENGTH,
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    SavedGearset,
)

SELECT_TYPE = "gearset-select"
UPDATE_TYPE = "gearset-update"
DELETE_TYPE = "gearset-delete"
DEFAULT_TYPE = "gearset-default"

LOADED_ICON = "tabler:check"
DEFAULT_ICON = "tabler:star"
DEFAULT_SET_ICON = "tabler:star-filled"
UPDATE_ICON = "tabler:device-floppy"
DELETE_ICON = "tabler:trash"

_ICON_SIZE = 18
_SELECTED_ROW_BG = "var(--mantine-color-blue-light)"


def gearset_pattern_id(
    component_type: str, gearset_id: str, cell: str | None = None
) -> dict[str, str]:
    """Build the pattern-matching ID for a per-gearset control.

    Parameters
    ----------
    component_type
        One of the ``*_TYPE`` constants.
    gearset_id
        ID of the gearset the control acts on.
    cell
        Distinguishes several controls of the same type on one row, such as the
        clickable cells that all select the row's gearset.

    Returns
    -------
    dict[str, str]
        A Dash pattern-matching component ID.
    """
    component_id = {"type": component_type, "gearset_id": gearset_id}
    if cell is not None:
        component_id["cell"] = cell
    return component_id


def _icon_button(
    icon: str,
    component_id: dict[str, str] | str,
    label: str,
    variant: str,
    color: str,
) -> dmc.Tooltip:
    """Create an icon-only action button with a tooltip and accessible name.

    Parameters
    ----------
    icon
        Iconify identifier, for example ``tabler:check``.
    component_id
        Dash ID of the button.
    label
        Tooltip text, also used as the button's ``aria-label``.
    variant
        Mantine ``ActionIcon`` variant.
    color
        Mantine colour name.

    Returns
    -------
    dmc.Tooltip
        The tooltip-wrapped icon button.
    """
    return dmc.Tooltip(
        dmc.ActionIcon(
            DashIconify(icon=icon, width=_ICON_SIZE),
            id=component_id,
            buttonProps={"aria-label": label},
            variant=variant,
            color=color,
        ),
        label=label,
        withArrow=True,
    )


def _select_cell(gearset: SavedGearset, cell: str, content) -> dmc.TableTd:
    """Create a table cell whose whole area loads the gearset when clicked.

    The cell holds a full-size button so the click target is the entire cell and
    remains keyboard accessible. Only the name cell is a tab stop.
    """
    aria_props: dict[str, Any] = {"aria-label": f"Load {gearset.name} into form"}
    return dmc.TableTd(
        dmc.UnstyledButton(
            content,
            id=gearset_pattern_id(SELECT_TYPE, gearset.id, cell),
            tabIndex=0 if cell == "name" else -1,
            style={
                "display": "block",
                "width": "100%",
                "textAlign": "left",
                "padding": "var(--table-vertical-spacing) var(--table-horizontal-spacing)",
            },
            **aria_props,
        ),
        p=0,
    )


def _gearset_row(gearset: SavedGearset, is_default: bool, is_selected: bool):
    """Create the table row for one saved gearset.

    Clicking the name or role cell loads the gearset into the form; the loaded
    row is highlighted and marked with a check.
    """
    name_children: list[DashIconify | dmc.Text | dmc.Badge] = []
    if is_selected:
        name_children.append(DashIconify(icon=LOADED_ICON, width=_ICON_SIZE))
    name_children.append(dmc.Text(gearset.name, style={"wordBreak": "break-word"}))
    if is_default:
        name_children.append(dmc.Badge("Default", size="sm"))
    name_content = dmc.Group(name_children, gap="xs", wrap="nowrap")

    default_label = "Clear default gearset" if is_default else "Set as default gearset"
    actions = dmc.Group(
        [
            _icon_button(
                DEFAULT_SET_ICON if is_default else DEFAULT_ICON,
                gearset_pattern_id(DEFAULT_TYPE, gearset.id),
                default_label,
                variant="subtle",
                color="yellow",
            ),
            _icon_button(
                UPDATE_ICON,
                gearset_pattern_id(UPDATE_TYPE, gearset.id),
                "Update from form",
                variant="subtle",
                color="gray",
            ),
            _icon_button(
                DELETE_ICON,
                gearset_pattern_id(DELETE_TYPE, gearset.id),
                "Delete gearset",
                variant="subtle",
                color="red",
            ),
        ],
        gap="xs",
        justify="flex-end",
        wrap="nowrap",
    )
    cells = [
        _select_cell(gearset, "name", name_content),
        _select_cell(gearset, "role", gearset.role.value),
        dmc.TableTd(actions),
    ]
    # An explicit ``bg=None`` stops the row from rendering, so only pass it when set.
    if is_selected:
        return dmc.TableTr(cells, bg=_SELECTED_ROW_BG)
    return dmc.TableTr(cells)


def gearset_table_rows(
    library: GearsetLibrary, selected_id: str | None
) -> list[dmc.TableTr]:
    """Create the table body rows for a library.

    Parameters
    ----------
    library
        Saved gearsets to display.
    selected_id
        ID of the gearset currently loaded in the form, if any.

    Returns
    -------
    list
        One row per gearset, or a single placeholder row when empty.
    """
    if not library.gearsets:
        return [
            dmc.TableTr(
                dmc.TableTd(
                    dmc.Text("No saved gearsets yet.", c="dimmed", size="sm"),
                    tableProps={"colSpan": 3},
                )
            )
        ]
    return [
        _gearset_row(
            gearset,
            is_default=gearset.id == library.default_id,
            is_selected=gearset.id == selected_id,
        )
        for gearset in library.gearsets
    ]


def loaded_gearset_badge(
    library: GearsetLibrary, selected_id: str | None
) -> dmc.Tooltip | None:
    """Create the badge naming the saved gearset loaded into the form.

    Parameters
    ----------
    library
        Saved gearsets to search.
    selected_id
        ID of the gearset currently loaded in the form, if any.

    Returns
    -------
    dmc.Tooltip | None
        A tooltip-wrapped badge with the gearset name, or ``None`` when no saved
        gearset is loaded.
    """
    gearset = library.get(selected_id)
    if gearset is None:
        return None
    return dmc.Tooltip(
        dmc.Badge(gearset.name, variant="light", size="lg"),
        label="Loaded from your saved gearsets",
        withArrow=True,
    )


def _gearset_table() -> dmc.TableScrollContainer:
    """Create the saved-gearset table; callbacks fill its body."""
    return dmc.TableScrollContainer(
        dmc.Table(
            [
                dmc.TableThead(
                    dmc.TableTr(
                        [
                            dmc.TableTh("Gearset"),
                            dmc.TableTh("Role", w=160),
                            dmc.TableTh("", w=140),
                        ]
                    )
                ),
                dmc.TableTbody(id="gearset-table-body"),
            ],
            highlightOnHover=True,
            verticalSpacing="xs",
        ),
        minWidth=520,
    )


def _delete_modal() -> dmc.Modal:
    """Create the delete-confirmation modal."""
    return dmc.Modal(
        [
            dmc.Stack(
                [
                    dmc.Text(id="gearset-delete-text"),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Cancel",
                                id="gearset-delete-cancel",
                                variant="default",
                            ),
                            dmc.Button(
                                "Delete",
                                id="gearset-delete-confirm",
                                color="red",
                            ),
                        ],
                        justify="flex-end",
                    ),
                ]
            )
        ],
        id="gearset-delete-modal",
        title="Delete gearset?",
        opened=False,
        centered=True,
    )


def _stores(apply_default: bool) -> list[dcc.Store]:
    """Create the browser and memory stores backing the manager.

    ``saved-gearsets`` and ``default-gear-index`` are the legacy app's storage
    keys; they are only read, once, to migrate into ``gearset-library``.
    """
    return [
        dcc.Store(id="gearset-library", storage_type="local"),
        dcc.Store(id="saved-gearsets", storage_type="local"),
        dcc.Store(id="default-gear-index", storage_type="local"),
        dcc.Store(id="selected-gearset-id"),
        dcc.Store(id="gearset-pending-delete"),
        dcc.Store(id="gearset-apply-default", data=apply_default),
    ]


def gearset_manager(apply_default: bool = True) -> dmc.Stack:
    """Create the saved-gearset manager, including its stores and modal.

    Parameters
    ----------
    apply_default
        Whether the default gearset should be loaded into the form on page
        load. Pass ``False`` when the form already shows a saved analysis.

    Returns
    -------
    dmc.Stack
        The stores, the collapsible manager, and the delete-confirmation modal.
    """
    panel = dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.TextInput(
                        id="new-gearset-name",
                        placeholder="Enter gearset name",
                        inputProps={"maxLength": MAX_GEARSET_NAME_LENGTH},
                        value="",
                        w={"base": "100%", "sm": 320},
                    ),
                    dmc.Button(
                        "Save as new set",
                        id="save-gearset-button",
                        disabled=True,
                    ),
                ],
                align="flex-end",
            ),
            dmc.Text(
                f"Saves the stats entered above. Up to {MAX_SAVED_GEARSETS} sets; "
                "click a set to load it, or use the star to load it automatically "
                "for new analyses.",
                size="sm",
                c="dimmed",
            ),
            dmc.Text(id="gearset-message", size="sm", c="red"),
            _gearset_table(),
        ],
        gap="sm",
    )
    return dmc.Stack(
        [
            *_stores(apply_default),
            _delete_modal(),
            dmc.Accordion(
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl("Manage saved gearsets"),
                        dmc.AccordionPanel(panel),
                    ],
                    value="saved-gearsets",
                ),
                id="saved-gearsets-accordion",
                variant="separated",
            ),
        ],
        gap=0,
    )
