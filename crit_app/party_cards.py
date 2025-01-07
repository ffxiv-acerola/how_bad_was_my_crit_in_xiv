from typing import Any, Dict, List, Optional, Union

import dash_bootstrap_components as dbc
import pandas as pd
from dash import (
    dash_table,
    dcc,
    html,
)

from crit_app.job_data.roles import abbreviated_job_map, role_stat_dict

QUICK_BUILD_TABLE_STYLES = {
    "header": {
        "backgroundColor": "rgb(30, 30, 30)",
        "color": "white",
        "font-family": "sans-serif",
        "font-size": "1.0em",
    },
    "data": {"backgroundColor": "rgb(50, 50, 50)", "color": "white"},
}

QUICK_BUILD_COLUMN_STYLES = [
    {
        "if": {"column_id": "job"},
        "width": "50px",
        "textAlign": "center",
        "padding-bottom": "4px",
        "font-family": "job-icons",
        "font-size": "1.3em",
    },
    {
        "if": {"column_id": "player_name"},
        "width": "200px",
        "textAlign": "left",
        "padding-left": "10px",
    },
]

party_analysis_assumptions_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle(html.H2("Limitations of party analysis"))),
        dbc.ModalBody(
            [
                html.P(
                    "While the analysis aims to be as accurate as possible, there are some assumptions and limitations that can affect its accuracy at predicting damage distributions and kill times. The damage distributions shown here likely have errors on the order of a few percentage points. Due to the exponential dropoff of kill time probability and density for damage distributions, the results reported here are sufficient for gauging the feasibility of achieving a particular kill time."
                ),
                html.H3("Stochastic rotations (procs)"),
                html.P(
                    "The number of usages for actions which have a random chance of occurring are not modeled. When procs are used, they generally require some sort of decision making, which cannot be easily inferred. Modeling procs also adds significant computational cost."
                ),
                html.H3("Discretization error"),
                html.P(
                    "The natural units for any sort of damage variability analysis is total damage dealt. The total damage dealt by a party for a boss encounter can be on the order of 10's of millions of damage points. A modest amount of discretization (10's to 100's of damage points) is used to reduce the computational and space requirements of arrays."
                ),
            ]
        ),
        dbc.ModalFooter(
            dbc.Button(
                "Close", id="party-analysis-close", className="ms-auto", n_clicks=0
            )
        ),
    ],
    id="party-analysis-modal",
    is_open=False,
    size="lg",
)


def create_fflogs_card(
    fflogs_url: Optional[str] = None,
    encounter_name=[],
    kill_time_str: str = "",
    phase_selector_value="0",
    phase_selector_options: list = [],
    phase_select_hidden: bool = False,
    medication_amount: int = 392,
    quick_build_table_data: list = [],
    party_accordion_items: list = [],
    analysis_progress_children="Analysis progress: Done!",
    analysis_progress_value: int = 100,
    hide_fflogs_div: bool = True,
    analyze_button_text: str = "Analyze party rotation",
    wrap_collapse: bool = False,
) -> dbc.Card:
    """
    Create card component for FFLogs URL input and encounter info.

    Args:
        fflogs_url: Link to FFLogs report and fight.
        encounter_info_children: Child components for encounter info section

    Returns:
        Bootstrap card containing URL input and encounter info
    """
    # URL input row
    url_input = dbc.Row(
        [
            dbc.Label("Log URL", width=12, md=2),
            dbc.Col(
                [
                    dbc.Input(
                        value=fflogs_url,
                        type="text",
                        placeholder="Enter FFLogs URL",
                        id="fflogs-url2",
                    ),
                    dbc.FormFeedback(type="invalid", id="fflogs-url-feedback2"),
                ],
                className="me-3",
            ),
            dbc.Col(
                dbc.Button(
                    "Submit",
                    color="primary",
                    id="fflogs-url-state2",
                ),
                width="auto",
            ),
        ],
        class_name="mb-3",
        style={"padding-bottom": "15px"},
    )

    # Encounter info row
    encounter_info = html.H3(
        [
            html.Span(encounter_name, id="party-encounter-name"),
            " (",
            html.Span(kill_time_str, id="party-kill-time"),
            ")",
        ]
    )

    # Display fight

    # Phase selection
    phase_select = html.Div(
        dbc.Row(
            children=[
                dbc.Label("Phase:", width=12, md=2, id="party-phase-label"),
                dbc.Col(
                    dbc.Select(
                        options=phase_selector_options,
                        value=phase_selector_value,
                        id="party-phase-select",
                    ),
                    width=1,
                    md=5,
                ),
            ],
        ),
        id="party-phase-select-div",
        style={"padding-bottom": "15px"},
        hidden=phase_select_hidden,
    )

    # Job build
    job_build_text = [
        html.H3("Enter job builds"),
        html.P(
            "Job builds for all players must be entered. "
            "Either enter the Etro link or input each job's stats. "
            "Do not include any party composition bonuses to the main stat, "
            "this is automatically calculated."
        ),
    ]

    # Medication
    medication_selector = create_tincture_input(medication_amount)

    # Quick build input
    # quick_build_div = create_quick_build_div(
    #     create_quick_build_table(etro_job_build_information)
    # )
    quick_build_table = dash_table.DataTable(
        data=quick_build_table_data,
        columns=[
            {"id": "job", "name": "Job", "editable": False, "selectable": False},
            {
                "id": "player_name",
                "name": "Player",
                "editable": False,
                "selectable": False,
            },
            {
                "id": "etro_link",
                "name": "Etro link",
                "editable": True,
                "selectable": True,
            },
        ],
        style_header=QUICK_BUILD_TABLE_STYLES["header"],
        style_data=QUICK_BUILD_TABLE_STYLES["data"],
        style_cell_conditional=QUICK_BUILD_COLUMN_STYLES,
        editable=True,
        id="quick-build-table",
    )

    quick_build_div = html.Div(
        [
            html.H4("Quick build input"),
            html.P(
                'Quickly input all Etro links by pasting them into the "Etro link" '
                "column below like you would a spreadsheet and then clicking the "
                '"Fill in Etro links" button. Otherwise, enter the build information '
                "one-by-one and then click the validate builds button."
            ),
            quick_build_table,
            html.Br(),
            dbc.Button("Fill in and apply Etro links", id="quick-build-fill-button"),
        ],
        style={"padding-top": "15px", "padding-bottom": "15px"},
    )

    # Party accordion
    party_accordion = dbc.ListGroup(
        children=party_accordion_items, id="party-accordion"
    )

    # Validate
    buttons = html.Div(
        [
            html.Div(
                [
                    dbc.Button(
                        analyze_button_text, id="party-compute", class_name="w-100"
                    )
                ],
                id="party-compute-div",
                hidden=True,
                className="w-100",
                style={"padding-top": "15px", "padding-bottom": "15px"},
            ),
        ],
        style={"padding-top": "15px"},
    )

    # Progress bar
    party_analysis_progress = [
        html.H4(analysis_progress_children, id="party-progress-header"),
        dbc.Progress(
            value=analysis_progress_value,
            style={"height": "25px"},
            color="#009670",
            id="party-progress",
        ),
        html.P(id="party-progress-job"),
    ]

    # Check whether to wrap things in a collapse to
    # hide the lengthy form
    if wrap_collapse:
        job_build_items = [
            dbc.Button(
                children="Show party build",
                n_clicks=0,
                id="party-collapse-button",
                class_name="w-100",
            ),
            dbc.Collapse(
                [
                    *job_build_text,
                    medication_selector,
                    quick_build_div,
                    party_accordion,
                    buttons,
                ],
                id="party-list-collapse",
                is_open=False,
                class_name="me-1",
            ),
        ]

    else:
        job_build_items = [
            html.Div(
                [
                    dbc.Button(
                        children="Show party build",
                        n_clicks=0,
                        id="party-collapse-button",
                        class_name="mb-3",
                    ),
                    dbc.Collapse(
                        id="party-list-collapse",
                    ),
                ],
                hidden=True,
            ),
            *job_build_text,
            medication_selector,
            quick_build_div,
            party_accordion,
            buttons,
        ]

    fflogs_hidden_div = html.Div(
        [
            encounter_info,
            phase_select,
            *job_build_items,
            *party_analysis_progress,
            html.Div(id="party-analysis-error"),
        ],
        id="party-fflogs-hidden-div",
        hidden=hide_fflogs_div,
    )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H2(
                    "Party analysis",
                    className="display-3",
                    style={"font-size": "2.5em"},
                ),
                html.P(
                    "Analyze damage variability for the whole party, "
                    "including the likelihood of faster kill times.",
                    className="lead",
                ),
                html.Hr(className="my-2"),
                html.H3("Enter log to analyze"),
                url_input,
                fflogs_hidden_div,
            ]
        )
    )


def create_results_card(
    analysis_url: str = "",
    party_dps_pdf_figure=None,
    kill_time_figure=None,
    player_analysis_selector_options=[],
    player_analysis_default=None,
):
    party_analysis_summary = html.Div(
        [
            dbc.Row(
                [
                    html.P(
                        [
                            "Scroll down to see a detailed analysis showing the DPS distribution of the party's rotation, how likely faster kill times are, and individual player DPS distributions. Click ",
                            html.A("here", href="#", id="party-analysis-open"),
                            " to learn more about the limitations and assumptions of the results.",
                            party_analysis_assumptions_modal,
                        ]
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Label("Copy analysis link"),
                        align="center",
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Input(
                            value=analysis_url,
                            disabled=True,
                            id="party-analysis-link",
                        ),
                        width=9,
                        align="center",
                    ),
                    dbc.Col(
                        dcc.Clipboard(
                            id="party-clipboard",
                            style={"display": "inline-block"},
                        ),
                        align="center",
                        width=1,
                    ),
                ]
            ),
        ]
    )

    # Party rotation DPS distribution
    party_dps_pdf = dbc.Card(
        dbc.CardBody(
            [
                html.H3("Party DPS distribution"),
                html.P(
                    "The graph below shows the DPS distribution for the whole party. Mouse over curves/points to view corresponding percentiles."
                ),
                dcc.Graph(figure=party_dps_pdf_figure),
            ]
        )
    )

    # Kill time analysis
    kill_time_card = html.Div(
        dbc.Card(
            dbc.CardBody(
                html.Div(
                    [
                        html.H3("Kill time analysis"),
                        html.P(
                            "The graph below estimates how likely the actual kill time was and how likely faster kill times are. The y-axis represents all kills that are equal to or faster than the kill time reported on the x-axis. Faster kill times are estimated by simply truncating the rotation of the party by the respective time amount. Note the y-axis is on a log scale."
                        ),
                        html.P(
                            "Low percent chances indicate that faster kill times with the given rotation are unlikely. Faster kill times may be achieved through means like further refining the party's rotation, performing a planned rotation more consistently, or generating more Limit Break usages."
                        ),
                        dcc.Graph(figure=kill_time_figure),
                    ]
                )
            )
        )
    )

    job_dps_selection = html.Div(
        [
            dbc.RadioItems(
                options=[
                    {"label": "Rotation DPS distribution", "value": "rotation"},
                    {"label": "Action DPS distributions", "value": "actions"},
                ],
                value="rotation",
                id="job-graph-type",
                inline=True,
            ),
            html.Br(),
            dcc.Dropdown(
                player_analysis_selector_options,
                value=player_analysis_default,
                id="job-selector",
                style={
                    "height": "45px",
                },
            ),
            html.Br(),
        ],
    )

    job_view_card = html.Div(
        dbc.Card(
            dbc.CardBody(
                html.Div(
                    [
                        html.H3("Job damage distributions"),
                        html.P(
                            "Click the drop-down to view the DPS distribution of a specific job. The radio buttons toggle between the overall rotation DPS distribution and the DPS distribution of each action. Mouse over curves/points to view corresponding percentiles."
                        ),
                        html.A(
                            [
                                "Open job-level analysis page  ",
                                html.I(
                                    className="fas fa-external-link-alt",
                                    style={"font-size": "0.8em"},
                                ),
                            ],
                            target="_blank",
                            id="job-level-analysis",
                        ),
                        html.Br(),
                        html.Br(),
                        job_dps_selection,
                        html.Br(),
                        dcc.Graph(id="job-rotation-pdf"),
                    ],
                    className="me-1",
                )
            )
        )
    )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H2("Party analysis results"),
                party_analysis_summary,
                html.Br(),
                party_dps_pdf,
                html.Br(),
                kill_time_card,
                html.Br(),
                job_view_card,
            ]
        )
    )


def create_quick_build_table_data(
    job_information: List[Dict[str, Any]],
) -> dash_table.DataTable:
    """
    Create quick build table with job and player information.

    Args:
        job_information: List of dicts containing job/player data

    Returns:
        Dash DataTable component with formatted job/player info
    """

    # Constants
    # ROLE_ORDER = {
    #     "Tank": 1,
    #     "Healer": 2,
    #     "Melee": 3,
    #     "Physical Ranged": 4,
    #     "Magical Ranged": 5
    # }

    # Create and sort dataframe
    quick_build = pd.DataFrame(job_information)
    # TODO: Verify this is correct
    # quick_build["role_order"] = quick_build["role"].map(ROLE_ORDER)
    quick_build["role_order"] = 1
    quick_build.loc[quick_build["role"] == "Healer", "role_order"] = 2
    quick_build.loc[quick_build["role"] == "Melee", "role_order"] = 3
    quick_build.loc[quick_build["role"] == "Physical Ranged", "role_order"] = 4
    quick_build.loc[quick_build["role"] == "Magical Ranged", "role_order"] = 5
    quick_build["job"] = quick_build["job"].map(abbreviated_job_map)
    quick_build["etro_link"] = None
    quick_build.loc[~quick_build["etro_id"].isna(), "etro_link"] = (
        "https://etro.gg/gearset/" + quick_build["etro_id"]
    )

    quick_build = quick_build.sort_values(
        ["role_order", "job", "player_name", "player_id"]
    )[["job", "player_name", "etro_link"]]

    return quick_build.to_dict("records")


def create_quick_build_div(quick_build_table: Any) -> html.Div:
    """
    Create div containing quick build input components.

    Args:
        quick_build_table: Dash DataTable for entering build info

    Returns:
        Div containing header, instructions, table and fill button
    """
    return html.Div(
        [
            html.H4("Quick build input"),
            html.P(
                'Quickly input all Etro links by pasting them into the "Etro link" '
                "column below like you would a spreadsheet and then clicking the "
                '"Fill in Etro links" button. Otherwise, enter the build information '
                "one-by-one and then click the validate builds button."
            ),
            quick_build_table,
            html.Br(),
            dbc.Button("Fill in Etro links", id="quick-build-fill-button"),
        ],
        style={"padding-top": "15px", "padding-bottom": "15px"},
    )


# FIXME: remove job and delay
def create_job_build_content(
    role: str,
    id_idx: int,
    job: Optional[str] = None,
    main_stat: Optional[int] = None,
    tenacity: Optional[int] = None,
    determination: Optional[int] = None,
    speed: Optional[int] = None,
    crit: Optional[int] = None,
    direct_hit: Optional[int] = None,
    weapon_damage: Optional[int] = None,
    delay: Optional[float] = None,
) -> html.Div:
    """
    Create form component for entering job build stats.

    Args:
        role: Job role (Tank, Healer, etc)
        id_idx: Index for component IDs
        job: Job abbreviation
        main_stat: Main stat value
        tenacity: Tenacity stat (tanks only)
        determination: Determination stat
        speed: Skill/spell speed stat
        crit: Critical hit stat
        direct_hit: Direct hit stat
        weapon_damage: Weapon damage value
        delay: Weapon delay value

    Returns:
        Div containing form with stat input fields
    """
    role_labels = role_stat_dict[role]
    top_stat_list = [
        dbc.Label(
            children=role_labels["main_stat"]["label"],
            width=12,
            md=1,
            id={"type": "main-stat-label", "index": id_idx},
        ),
        dbc.Col(
            dbc.Input(
                value=main_stat,
                type="number",
                placeholder=role_labels["main_stat"]["placeholder"],
                id={"type": "main-stat", "index": id_idx},
            )
        ),
        dbc.Label(
            children="DET:",
            width=12,
            md=1,
            id={"type": "det-label", "index": id_idx},
        ),
        dbc.Col(
            dbc.Input(
                value=determination,
                type="number",
                placeholder="Determination",
                id={"type": "DET", "index": id_idx},
            )
        ),
        dbc.Label(
            children=[
                html.Span(
                    children=role_labels["speed_stat"]["label"],
                    id=f"speed-tooltip-{id_idx}",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Your Skill/Spell Speed stat, not your GCD.",
                    target=f"speed-tooltip-{id_idx}",
                ),
                dbc.FormFeedback(
                    "Please enter your Skill/Spell Speed stat, not GCD.",
                    type="invalid",
                    id=f"speed-feedback-{id_idx}",
                ),
            ],
            width=12,
            md=1,
            id=f"speed-stat-label-{id_idx}",
        ),
        dbc.Col(
            dbc.Input(
                value=speed,
                type="number",
                placeholder=role_labels["speed_stat"]["placeholder"],
                # min=100,
                # max=4000,
                id={"type": "speed-stat", "index": id_idx},
            )
        ),
    ]

    bottom_stat_list = [
        dbc.Label("CRT:", width=12, md=1, id={"type": "crt-label", "index": id_idx}),
        dbc.Col(
            dbc.Input(
                value=crit,
                type="number",
                placeholder="Critical Hit",
                id={"type": "CRT", "index": id_idx},
            )
        ),
        dbc.Label("DH:", width=12, md=1, id={"type": "dh-label", "index": id_idx}),
        dbc.Col(
            dbc.Input(
                value=direct_hit,
                type="number",
                placeholder="Direct Hit",
                id={"type": "DH", "index": id_idx},
            )
        ),
        dbc.Label("WD:", width=12, md=1, id={"type": "wd-label", "index": id_idx}),
        dbc.Col(
            dbc.Input(
                value=weapon_damage,
                type="number",
                placeholder="Weapon Damage",
                id={"type": "WD", "index": id_idx},
            )
        ),
    ]

    tenacity_stat_list = [
        dbc.Label("TEN:", width=12, md=1, id="tenacity-label"),
        dbc.Col(
            dbc.Input(
                value=tenacity,
                type="number",
                placeholder="Tenacity",
                min=100,
                max=6000,
                id={"type": "TEN", "index": id_idx},
            ),
            width=12,
            md=3,
        ),
    ]

    # Stat fields
    top_stat_row = dbc.Row(
        top_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )
    bottom_stat_row = dbc.Row(
        bottom_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )
    tenacity_stat_row = html.Div(
        dbc.Row(tenacity_stat_list, class_name="g-2", style={"padding-bottom": "15px"}),
        id={"type": "tenacity-row", "index": id_idx},
    )

    return html.Div(
        dbc.Form(
            [
                html.H4(id={"type": "build-name", "index": id_idx}),
                top_stat_row,
                bottom_stat_row,
                tenacity_stat_row,
            ]
        )
    )


def create_tincture_input(
    medication_amt: int = 392, id_name: str = "party-tincture-grade"
) -> html.Div:
    """
    Create medication (tincture) selection component.

    Args:
        medication_amt: Default medication amount bonus
        id_name: Component ID for select element

    Returns:
        Div containing medication grade selector
    """
    tincture_input = html.Div(
        [
            html.H4("Medication"),
            html.P(
                "Select the medication (pot) used, which will be applied to all party members."
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Select(
                                name="POT:",
                                id=id_name,
                                options=[
                                    {
                                        "label": "Grade 2 Gemdraught (+392)",
                                        "value": 392,
                                    },
                                    {
                                        "label": "Grade 1 Gemdraught (+361)",
                                        "value": 351,
                                    },
                                    {
                                        "label": "Grade 8 Tincture (+262)",
                                        "value": 262,
                                    },
                                    {
                                        "label": "Grade 7 Tincture (+223)",
                                        "value": 223,
                                    },
                                ],
                                value=medication_amt,
                            ),
                        ],
                        width=12,
                        md=5,
                    ),
                ],
                style={"padding-bottom": "15px"},
            ),
        ]
    )
    return tincture_input


def create_accordion_items(
    role: str,
    job: str,
    name: str,
    player_id: int,
    id_idx: int,
    main_stat: Optional[int] = None,
    secondary_stat: Optional[int] = None,
    determination: Optional[int] = None,
    speed: Optional[int] = None,
    crit: Optional[int] = None,
    direct_hit: Optional[int] = None,
    weapon_damage: Optional[int] = None,
    delay: Optional[float] = None,
    etro_url: Optional[str] = None,
) -> dbc.AccordionItem:
    """
    Create accordion item for job build input.

    Args:
        role: Job role (Tank, Healer, etc)
        job: Job abbreviation
        name: Player name
        player_id: Player identifier
        id_idx: Index for component IDs
        main_stat: Main stat value
        secondary_stat: Secondary stat value
        determination: Determination stat
        speed: Skill/spell speed stat
        crit: Critical hit stat
        direct_hit: Direct hit stat
        weapon_damage: Weapon damage value
        delay: Weapon delay value
        etro_url: Link to Etro build

    Returns:
        AccordionItem containing job build input form

    Example:
        >>> item = create_accordion_items("Tank", "WAR", "Player1", 123, 0)
    """
    name_and_job = html.P(
        [
            html.Span(
                abbreviated_job_map[job],
                style={
                    "font-family": "job-icons",
                    "font-size": "1.4em",
                    "position": "relative",
                    "top": "4px",
                },
                id={"type": "job-name", "index": id_idx},
            ),
            " ",
            html.Span(name, id={"type": "player-name", "index": id_idx}),
            html.Span(
                player_id,
                style={"opacity": "0%"},
                id={"type": "player-id", "index": id_idx},
            ),
        ]
    )
    return dbc.AccordionItem(
        children=create_job_build_content(
            role,
            id_idx,
            job,
            main_stat,
            secondary_stat,
            determination,
            speed,
            crit,
            direct_hit,
            weapon_damage,
            delay,
        ),
        title=[
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Label(
                            name_and_job,
                            id={"type": "name", "index": id_idx},
                        ),
                        md=2,
                        width=12,
                    ),
                    dbc.Col(
                        [
                            dbc.Input(
                                value=etro_url,
                                placeholder=f"Enter Etro build for {name}",
                                id={"type": "etro-input", "index": id_idx},
                            ),
                            dbc.FormFeedback(
                                type="invalid",
                                id={"type": "etro-feedback", "index": id_idx},
                            ),
                        ],
                        md=9,
                        width=12,
                        className="h-50",
                    ),
                ],
                class_name="g-2 w-100",
            )
        ],
        id={"type": "accordion", "index": id_idx},
    )


def create_party_accordion_children(
    job_information: List[Dict[str, Union[str, int, float, None]]],
    job_build_present: bool = False,
) -> list:
    """
    Create accordion UI component grouping party members by role.

    Args:
        job_information: List of dicts containing player/job data:
            - role: Job role (Tank, Healer, etc)
            - job: Job abbreviation
            - player_name: Character name
            - player_id: Player identifier
            Optional build stats if job_build_present:
            - main_stat_pre_bonus: Pre-bonus main stat
            - secondary_stat_pre_bonus: Pre-bonus secondary stat
            - determination: Determination value
            - speed: Skill/spell speed value
            - critical_hit: Critical hit value
            - direct_hit: Direct hit value
            - weapon_damage: Weapon damage value
            - delay: Weapon delay value
            - etro_id: Etro build ID
        job_build_present: Whether job build stats are included

    Returns:
        ListGroup containing accordion sections for each role
    """
    tanks = []
    healers = []
    melee = []
    physical_ranged = []
    casters = []

    job_information = sorted(
        job_information, key=lambda d: (d["job"], d["player_name"], d["player_id"])
    )

    for idx, j in enumerate(job_information):
        if job_build_present:
            main_stat = j["main_stat_pre_bonus"]
            secondary_stat = j["secondary_stat_pre_bonus"]
            determination = j["determination"]
            speed = j["speed"]
            crit = j["critical_hit"]
            direct_hit = j["direct_hit"]
            weapon_damage = j["weapon_damage"]
            delay = j["delay"]
            etro_id = j["etro_id"]

            if etro_id is None:
                etro_url = None
            else:
                etro_url = f"https://etro.gg/gearset/{etro_id}"
        else:
            main_stat = None
            secondary_stat = None
            determination = None
            speed = None
            crit = None
            direct_hit = None
            weapon_damage = None
            delay = None
            etro_url = None

        if j["role"] == "Tank":
            tanks.append(
                create_accordion_items(
                    j["role"],
                    j["job"],
                    j["player_name"],
                    j["player_id"],
                    idx,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    etro_url,
                )
            )

        elif j["role"] == "Healer":
            healers.append(
                create_accordion_items(
                    j["role"],
                    j["job"],
                    j["player_name"],
                    j["player_id"],
                    idx,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    etro_url,
                )
            )

        elif j["role"] == "Melee":
            melee.append(
                create_accordion_items(
                    j["role"],
                    j["job"],
                    j["player_name"],
                    j["player_id"],
                    idx,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    etro_url,
                )
            )

        elif j["role"] == "Physical Ranged":
            physical_ranged.append(
                create_accordion_items(
                    j["role"],
                    j["job"],
                    j["player_name"],
                    j["player_id"],
                    idx,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    etro_url,
                )
            )

        elif j["role"] == "Magical Ranged":
            casters.append(
                create_accordion_items(
                    j["role"],
                    j["job"],
                    j["player_name"],
                    j["player_id"],
                    idx,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    etro_url,
                )
            )

    return [
        dbc.ListGroupItem(
            [
                html.H4("Tank"),
                dbc.Accordion(
                    tanks,
                    start_collapsed=True,
                ),
            ],
        ),
        dbc.ListGroupItem(
            [
                html.H4("Healer"),
                dbc.Accordion(
                    healers,
                    start_collapsed=True,
                ),
            ]
        ),
        dbc.ListGroupItem(
            [
                html.H4("Melee"),
                dbc.Accordion(
                    melee,
                    start_collapsed=True,
                ),
            ]
        ),
        dbc.ListGroupItem(
            [
                html.H4("Physical Ranged"),
                dbc.Accordion(
                    physical_ranged,
                    start_collapsed=True,
                ),
            ]
        ),
        dbc.ListGroupItem(
            [
                html.H4("Magical Ranged"),
                dbc.Accordion(
                    casters,
                    start_collapsed=True,
                ),
            ]
        ),
    ]
