"""Dash Mantine Components builders for job-stats UI."""

from typing import Optional

import dash_mantine_components as dmc

from crit_app_v2.job_stats.models import Role
from crit_app_v2.job_stats.ranges import STAT_RANGES
from crit_app_v2.job_stats.roles import ROLE_SPECS

ROLE_OPTIONS = [{"label": role.value, "value": role.value} for role in Role]


def _stat_input(
    label: str,
    input_id: str,
    value: Optional[int],
    placeholder: str,
    stat_range_key: str,
    description: Optional[str] = None,
) -> dmc.NumberInput:
    """Create a consistently labelled stat input for the Mantine workbench."""
    stat_range = STAT_RANGES[stat_range_key]
    return dmc.NumberInput(
        id=input_id,
        label=label,
        value=value,
        placeholder=placeholder,
        description=description,
        min=stat_range.lower,
        max=stat_range.upper,
        clampBehavior="strict",
        allowDecimal=False,
        thousandSeparator=",",
    )


def initialize_job_build(
    job_build_url: Optional[str] = None,
    role: Role | str = Role.HEALER,
    main_stat: Optional[int] = None,
    tenacity: Optional[int] = None,
    determination: Optional[int] = None,
    speed: Optional[int] = None,
    crit: Optional[int] = None,
    direct_hit: Optional[int] = None,
    weapon_damage: Optional[int] = None,
    build_selector_hidden: bool = True,
) -> dmc.Paper:
    """Create the player-analysis job-stats form."""
    build_selector_style = {"display": "none"} if build_selector_hidden else {}
    selected_role = Role(role)
    role_spec = ROLE_SPECS[selected_role]

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
                                    id="dmc-job-build-url",
                                    label="Gearset URL",
                                    value=job_build_url,
                                    placeholder="Enter etro.gg / xivgear.app build URL",
                                ),
                                span={"base": 12, "md": 9},
                            ),
                            dmc.GridCol(
                                dmc.Button(
                                    "Submit",
                                    id="dmc-job-build-url-button",
                                    fullWidth=True,
                                ),
                                span={"base": 12, "md": 3},
                                style={"display": "flex", "alignItems": "flex-end"},
                            ),
                        ],
                        gutter="md",
                    ),
                    dmc.Select(
                        id="dmc-role-select",
                        label="Role",
                        data=ROLE_OPTIONS,
                        value=selected_role.value,
                        allowDeselect=False,
                        w={"base": "100%", "md": "50%"},
                    ),
                    dmc.Select(
                        id="dmc-xiv-gear-select",
                        label="Select build",
                        data=[],
                        placeholder="Choose a gearset from this sheet",
                        style=build_selector_style,
                    ),
                    dmc.Stack(
                        [
                            dmc.Title("Job stats", order=3),
                            dmc.Text(
                                "Do not include any percent bonus to main stat; "
                                "it is calculated automatically.",
                                c="dimmed",
                            ),
                            dmc.Grid(
                                [
                                    dmc.GridCol(
                                        _stat_input(
                                            role_spec.main_stat_placeholder,
                                            "dmc-main-stat",
                                            main_stat,
                                            role_spec.main_stat_placeholder,
                                            "main_stat",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            "Determination",
                                            "dmc-DET",
                                            determination,
                                            "Determination",
                                            "determination",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            role_spec.speed_stat_placeholder,
                                            "dmc-speed-stat",
                                            speed,
                                            role_spec.speed_stat_placeholder,
                                            "speed_stat",
                                            "Enter the stat, not your GCD.",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            "Critical Hit",
                                            "dmc-CRT",
                                            crit,
                                            "Critical Hit",
                                            "critical_hit",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            "Direct Hit",
                                            "dmc-DH",
                                            direct_hit,
                                            "Direct Hit",
                                            "direct_hit",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            "Weapon Damage",
                                            "dmc-WD",
                                            weapon_damage,
                                            "Weapon Damage",
                                            "weapon_damage",
                                        ),
                                        span={"base": 12, "sm": 6, "md": 4},
                                    ),
                                    dmc.GridCol(
                                        _stat_input(
                                            "Tenacity",
                                            "dmc-TEN",
                                            tenacity,
                                            "Tenacity",
                                            "tenacity",
                                        ),
                                        id="dmc-bottom-build-row",
                                        span={"base": 12, "sm": 6, "md": 4},
                                        style={
                                            "display": "block"
                                            if role_spec.requires_tenacity
                                            else "none"
                                        },
                                    ),
                                ],
                                gutter="md",
                            ),
                        ],
                        gap="sm",
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
                        id="dmc-saved-gearsets-accordion",
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
