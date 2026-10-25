"""Player-analysis job-stats workbench."""

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback

from crit_app_v2.job_stats import (
    ROLE_SPECS,
    STAT_INPUTS,
    Role,
    Stats,
    validate_job_stats_form,
)
from crit_app_v2.ui.job_stats import player_analysis_job_build

dash.register_page(__name__, path="/analysis")

encounter = dmc.Paper(
    [
        dmc.Stack(
            [
                dmc.Title("Enter log to analyze"),
                dmc.Grid(
                    [
                        dmc.GridCol(
                            dmc.TextInput(
                                id="job-build-url",
                                label="Log URL",
                                value="",
                                placeholder="https://www.fflogs.com/reports/...",
                            ),
                            span={"base": 12, "md": 9},
                        ),
                        dmc.GridCol(
                            dmc.Button(
                                "Submit",
                                id="job-build-url-button",
                                fullWidth=True,
                                disabled=True,
                            ),
                            span={"base": 12, "md": 3},
                            style={"display": "flex", "alignItems": "flex-end"},
                        ),
                    ],
                    gutter="md",
                ),
                dmc.Title("Encounter name (mm:ss)", id="encounter-name-time", order=3),
                dmc.Select(
                    label="Phase",
                    data=["Entire Fight", "Phase 1", "Phase 2"],
                    allowDeselect=False,
                    value="Entire Fight",
                    w={"base": "100%", "md": "50%"},
                ),
                # TODO: make info button with the tooltip
                dmc.Tooltip(
                    dmc.Title("Select a job", order=4),
                    label="Use the role selector to analyze jobs in another role.",
                ),
            ]
        )
    ],
    withBorder=True,
    shadow="sm",
    radius="md",
    p="xl",
)


def layout():
    """Render the initial player-analysis job-stats form."""
    return dmc.Container(
        [
            player_analysis_job_build(
                # "hello",
                # Role("Tank"),
                # 4000,
                # 800,
                # 3000,
                # 500,
                # 3000,
                # 2000,
                # 190,
            ),
            dmc.Space(),
            encounter,
        ],
        size="xl",
        py="xl",
    )


@callback(
    Output("main-stat-input-wrapper", "label"),
    Output("speed-stat-input-wrapper", "label"),
    Output("bottom-build-row", "style"),
    Input("role-select", "value"),
)
def role_stat_labels(selected_role: Role):
    style = {
        "display": "block" if ROLE_SPECS[selected_role].requires_tenacity else "none"
    }
    return (
        STAT_INPUTS[Stats.MAIN_STAT].stat_label(Role(selected_role)),
        STAT_INPUTS[Stats.SPEED_STAT].stat_label(Role(selected_role)),
        style,
    )


@callback(
    Output("job-build-url-button", "disabled"),
    Output("main-stat-input-wrapper", "error"),
    Output("determination-stat-input-wrapper", "error"),
    Output("speed-stat-input-wrapper", "error"),
    Output("critical-hit-stat-input-wrapper", "error"),
    Output("direct-hit-stat-input-wrapper", "error"),
    Output("weapon-damage-stat-input-wrapper", "error"),
    Output("tenacity-stat-input-wrapper", "error"),
    Input("role-select", "value"),
    Input("main-stat-input", "value"),
    Input("determination-stat-input", "value"),
    Input("speed-stat-input", "value"),
    Input("critical-hit-stat-input", "value"),
    Input("direct-hit-stat-input", "value"),
    Input("weapon-damage-stat-input", "value"),
    Input("tenacity-stat-input", "value"),
)
def job_build_validator(
    selected_role: Role,
    main_stat: int | None,
    determination: int | None,
    speed_stat: int | None,
    critical_hit: int | None,
    direct_hit: int | None,
    weapon_damage: int | None,
    tenacity: int | None,
):
    """
    Checks if all job stats are entered and are valid.

    If they are, the FFLogs URL submit button can be pressed.
    If not, it is disabled.
    """
    stats = {
        Stats.MAIN_STAT: main_stat,
        Stats.DETERMINATION: determination,
        Stats.SPEED_STAT: speed_stat,
        Stats.CRITICAL_HIT: critical_hit,
        Stats.DIRECT_HIT: direct_hit,
        Stats.WEAPON_DAMAGE: weapon_damage,
        Stats.TENACITY: tenacity,
    }
    result = validate_job_stats_form(selected_role, stats)
    return (
        not result.is_valid,
        result.errors[Stats.MAIN_STAT],
        result.errors[Stats.DETERMINATION],
        result.errors[Stats.SPEED_STAT],
        result.errors[Stats.CRITICAL_HIT],
        result.errors[Stats.DIRECT_HIT],
        result.errors[Stats.WEAPON_DAMAGE],
        result.errors[Stats.TENACITY],
    )
