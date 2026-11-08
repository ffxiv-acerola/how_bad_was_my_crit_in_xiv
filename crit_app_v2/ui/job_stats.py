"""Dash Mantine components for player and party job-stat forms."""

import dash_mantine_components as dmc
from dash import dcc

from crit_app_v2.game_data import (
    ROLE_SPECS,
    SPEED_STAT_SPEC,
    STAT_INPUTS,
    Role,
    StatInput,
    Stats,
)

ROLE_OPTIONS = [{"label": role.value, "value": role.value} for role in Role]


def _stat_input(
    value: int | None,
    stat_input: StatInput,
    role: Role,
    input_id: str,
    description: str | None = None,
):
    """Create a labeled numeric input using the stat's allowed range.

    The role determines the main- and speed-stat labels; other fields use the
    stat name. The input renders its own label, description, and validation
    error.
    """
    if stat_input.stat_name is Stats.MAIN_STAT:
        label = ROLE_SPECS[role].main_stat_label
    elif stat_input.stat_name is Stats.SPEED_STAT:
        label = SPEED_STAT_SPEC[ROLE_SPECS[role].speed_stat].display_name
    else:
        label = stat_input.stat_name.replace("_", " ").capitalize()

    return dmc.NumberInput(
        label=label,
        description=description,
        value=value,
        placeholder=stat_input.placeholder_text(),
        min=stat_input.lower,
        max=stat_input.upper,
        id=input_id,
        error=None,
        inputWrapperOrder=["label", "description", "error", "input"],
        withAsterisk=False,
        clampBehavior="none",
        allowDecimal=False,
        thousandSeparator=",",
    )


def _create_stat_grid(
    role: Role | str = Role.HEALER,
    main_stat: int | None = None,
    determination: int | None = None,
    speed: int | None = None,
    critical_hit: int | None = None,
    direct_hit: int | None = None,
    weapon_damage: int | None = None,
    tenacity: int | None = None,
) -> dmc.Stack:
    """Create a responsive grid of stat inputs for the selected role."""
    selected_role = Role(role)
    role_spec = ROLE_SPECS[selected_role]
    stat_input_span = {"base": 12, "sm": 6, "md": 4}

    stat_grid = dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Title("Job stats", order=3),
                    dmc.Tooltip(
                        dmc.ActionIcon(
                            children="ⓘ",
                            id="job-stats-info",
                            buttonProps={"aria-label": "Job stat input guidance"},
                            variant="subtle",
                            color="gray",
                            size="sm",
                        ),
                        label=dmc.List(
                            [
                                dmc.ListItem("Do not include 5% bonus to main stat."),
                                dmc.ListItem("Include any food stat bonuses."),
                            ],
                            size="sm",
                            spacing="xs",
                        ),
                        withArrow=True,
                        multiline=True,
                        w=280,
                    ),
                ],
                align="center",
                gap="xs",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        _stat_input(
                            value=main_stat,
                            stat_input=STAT_INPUTS[Stats.MAIN_STAT],
                            role=selected_role,
                            input_id="main-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=determination,
                            stat_input=STAT_INPUTS[Stats.DETERMINATION],
                            role=selected_role,
                            input_id="determination-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=speed,
                            stat_input=STAT_INPUTS[Stats.SPEED_STAT],
                            role=selected_role,
                            input_id="speed-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=critical_hit,
                            stat_input=STAT_INPUTS[Stats.CRITICAL_HIT],
                            role=selected_role,
                            input_id="critical-hit-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=direct_hit,
                            stat_input=STAT_INPUTS[Stats.DIRECT_HIT],
                            role=selected_role,
                            input_id="direct-hit-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=weapon_damage,
                            stat_input=STAT_INPUTS[Stats.WEAPON_DAMAGE],
                            role=selected_role,
                            input_id="weapon-damage-stat-input",
                        ),
                        span=stat_input_span,
                    ),
                    dmc.GridCol(
                        _stat_input(
                            value=tenacity,
                            stat_input=STAT_INPUTS[Stats.TENACITY],
                            role=selected_role,
                            input_id="tenacity-stat-input",
                        ),
                        id="bottom-build-row",
                        span=stat_input_span,
                        style={
                            "display": "block"
                            if role_spec.requires_tenacity
                            else "none"
                        },
                    ),
                ],
                gap="md",
            ),
        ],
        gap="sm",
    )

    return stat_grid


def player_analysis_job_build(
    job_build_url: str | None = None,
    role: Role = Role.HEALER,
    main_stat: int | None = None,
    tenacity: int | None = None,
    determination: int | None = None,
    speed_stat: int | None = None,
    critical_hit: int | None = None,
    direct_hit: int | None = None,
    weapon_damage: int | None = None,
    build_selector_hidden: bool = True,
) -> dmc.Paper:
    """Create the player-analysis job-stats form."""
    build_selector_style = {"display": "none"} if build_selector_hidden else {}
    selected_role = Role(role)

    return dmc.Paper(
        [
            dmc.Stack(
                [
                    dmc.Title("Player analysis", order=1),
                    dmc.Text("Analyze damage variability for a single player."),
                    dmc.Divider(),
                    dmc.Title("Select a role and enter gearset", order=3),
                    dmc.Text(
                        "A gearset must be fully entered before a log can be "
                        "analyzed. You can load a build from an etro.gg / "
                        "xivgear.app URL, or manually enter the values.",
                        c="dimmed",
                    ),
                    dmc.Grid(
                        [
                            dmc.GridCol(
                                dmc.TextInput(
                                    id="gearset-url",
                                    label="Gearset URL",
                                    value=job_build_url,
                                    placeholder="Enter etro.gg / xivgear.app build URL",
                                    error=None,
                                ),
                                span={"base": 12, "md": 9},
                            ),
                            dmc.GridCol(
                                dmc.Button(
                                    "Submit",
                                    id="gearset-url-button",
                                    fullWidth=True,
                                ),
                                span={"base": 12, "md": 3},
                                style={"display": "flex", "alignItems": "flex-end"},
                            ),
                        ],
                        gap="md",
                    ),
                    dmc.Select(
                        id="xiv-gear-select",
                        label="Select build",
                        data=[],
                        placeholder="Choose a gearset from this sheet",
                        style=build_selector_style,
                        value=None,
                        allowDeselect=False,
                    ),
                    dmc.Select(
                        id="role-select",
                        label="Role",
                        data=ROLE_OPTIONS,
                        value=selected_role.value,
                        allowDeselect=False,
                        w={"base": "100%", "md": "50%"},
                    ),
                    dcc.Store(id="loaded-job-build"),
                    _create_stat_grid(
                        selected_role,
                        main_stat,
                        determination,
                        speed_stat,
                        critical_hit,
                        direct_hit,
                        weapon_damage,
                        tenacity,
                    ),
                    dmc.Accordion(
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("Manage saved gearsets"),
                                dmc.AccordionPanel(
                                    dmc.Text(
                                        "Saved gearset management is not available yet.",
                                        c="dimmed",
                                    )
                                ),
                            ],
                            value="saved-gearsets",
                        ),
                        id="saved-gearsets-accordion",
                        variant="separated",
                    ),
                ],
                gap="md",
            )
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        p="xl",
    )


def party_analysis_job_build():
    """Placeholder for the party-analysis job-stat form; not implemented."""
    pass
