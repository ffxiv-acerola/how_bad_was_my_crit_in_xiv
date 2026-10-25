import dash_mantine_components as dmc

from crit_app_v2.job_stats.models import Role
from crit_app_v2.job_stats.roles import ROLE_SPECS
from crit_app_v2.job_stats.stats import STAT_INPUTS, StatInput, Stats

ROLE_OPTIONS = [{"label": role.value, "value": role.value} for role in Role]


def _stat_input(
    value: int | None,
    stat_input: StatInput,
    role: Role,
    input_id: str,
    description: int | None = None,
):
    """Create input form based on the role and stat."""
    number_input = dmc.NumberInput(
        value=value,
        placeholder=stat_input.placeholder_text(),
        min=stat_input.lower,
        max=stat_input.upper,
        id=input_id,
        clampBehavior="none",
        allowDecimal=False,
        thousandSeparator=",",
    )

    return dmc.InputWrapper(
        id=f"{input_id}-wrapper",
        label=stat_input.stat_label(role),
        description=description,
        error=None,
        inputWrapperOrder=["label", "description", "error", "input"],
        withAsterisk=False,
        children=number_input,
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
    """Creates stacks of stat inputs."""
    selected_role = Role(role)
    role_spec = ROLE_SPECS[selected_role]
    stat_input_span = {"base": 12, "sm": 6, "md": 4}

    stat_grid = dmc.Stack(
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
                gutter="md",
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
                                    id="job-build-url",
                                    label="Gearset URL",
                                    value=job_build_url,
                                    placeholder="Enter etro.gg / xivgear.app build URL",
                                ),
                                span={"base": 12, "md": 9},
                            ),
                            dmc.GridCol(
                                dmc.Button(
                                    "Submit",
                                    id="job-build-url-button",
                                    fullWidth=True,
                                ),
                                span={"base": 12, "md": 3},
                                style={"display": "flex", "alignItems": "flex-end"},
                            ),
                        ],
                        gutter="md",
                    ),
                    dmc.Select(
                        id="role-select",
                        label="Role",
                        data=ROLE_OPTIONS,
                        value=selected_role.value,
                        allowDeselect=False,
                        w={"base": "100%", "md": "50%"},
                    ),
                    dmc.Select(
                        id="xiv-gear-select",
                        label="Select build",
                        data=[],
                        placeholder="Choose a gearset from this sheet",
                        style=build_selector_style,
                    ),
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
    pass
