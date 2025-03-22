"""Create cards used to display content."""

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html
from plotly.graph_objs._figure import Figure

from crit_app.job_data.encounter_data import stat_ranges


def initialize_job_build(
    job_build_url: str | None = None,
    role: str = "Healer",
    main_stat: int | None = None,
    tenacity: int | None = None,
    determination: int | None = None,
    speed: int | None = None,
    crit: int | None = None,
    direct_hit: int | None = None,
    weapon_damage: int | None = None,
    delay: int | None = None,
    party_bonus: float = 1.05,
    medication_amt: int = 392,
    build_selector_hidden: bool = True,
) -> html.Div:
    """
    Create job build card with stat inputs and role selection.

    The card allows:
    - Loading builds from etro/xivgear URLs
    - Manual stat entry with validation
    - Role selection
    - Medication/tincture selection

    Args:
        job_build_url: Optional job build URL to preload stats (etro.gg or xivgear.api)
        role: Selected role (Tank/Healer/etc)
        main_stat: Main stat value for selected role
        tenacity: Tenacity stat (tanks only)
        determination: Determination stat
        speed: Skill/Spell speed stat
        crit: Critical hit stat
        direct_hit: Direct hit stat
        weapon_damage: Weapon damage stat
        delay: Weapon delay value
        party_bonus: Party composition bonus multiplier
        medication_amt: Amount of main stat from tincture/food

    Returns:
        html.Div containing the complete job build card
    """

    job_build_input = dbc.Row(
        [
            dbc.Label("Job build URL", width=12, md=2),
            dbc.Col(
                [
                    dbc.Input(
                        value=job_build_url,
                        type="text",
                        placeholder="Enter etro.gg / xivgear.app build URL",
                        id="job-build-url",
                    ),
                    dbc.FormFeedback(
                        type="invalid",
                        id="job-build-url-feedback",
                    ),
                ],
                className="me-3",
            ),
            dbc.Col(
                dbc.Button(
                    "Submit",
                    color="primary",
                    id="job-build-url-button",
                ),
                width="auto",
            ),
        ],
        class_name="mb-3",
    )

    role_input = dbc.Row(
        [
            dbc.Label("Role", width=12, md=2),
            dbc.Col(
                [
                    dbc.Select(
                        [
                            "Tank",
                            "Healer",
                            "Melee",
                            "Physical Ranged",
                            "Magical Ranged",
                        ],
                        role,
                        id="role-select",
                    )
                ],
                width=12,
                md=5,
            ),
        ],
        class_name="mb-3",
    )

    xiv_gear_select = html.Div(
        dbc.Row(
            [
                dbc.Label("Select build:", width=12, md=2),
                dbc.Col(
                    [
                        dbc.Select(
                            [
                                "A",
                                "B",
                                "C",
                            ],
                            value=None,
                            id="xiv-gear-select",
                        )
                    ],
                    width=12,
                    md=5,
                ),
            ]
        ),
        hidden=build_selector_hidden,
        id="xiv-gear-set-div",
    )

    tincture_input = dbc.Row(
        [
            dbc.Label(
                [
                    html.Span(
                        "POT:",
                        id="tincture-tooltip",
                        style={
                            "textDecoration": "underline",
                            "textDecorationStyle": "dotted",
                            "cursor": "pointer",
                        },
                    ),
                    dbc.Tooltip(
                        "Medication/potion. If no medication was used, "
                        "keep the default value selected.",
                        target="tincture-tooltip",
                    ),
                ],
                width=12,
                md=1,
            ),
            dbc.Col(
                [
                    dbc.Select(
                        name="POT:",
                        id="tincture-grade",
                        options=[
                            {"label": "Grade 2 Gemdraught (+392)", "value": 392},
                            {"label": "Grade 1 Gemdraught (+361)", "value": 351},
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
        ]
    )

    top_stat_list = [
        dbc.Label(children=None, width=12, md=1, id="main-stat-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=main_stat,
                    type="number",
                    placeholder=None,
                    id="main-stat",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['main_stat']['lower']} - {stat_ranges['main_stat']['upper']}",
                    type="invalid",
                ),
            ]
        ),
        dbc.Label(children="DET:", width=12, md=1, id="det-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=determination,
                    type="number",
                    placeholder="Determination",
                    id="DET",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['DET']['lower']} - {stat_ranges['DET']['upper']}",
                    type="invalid",
                ),
            ]
        ),
        dbc.Label(
            children=[
                html.Span(
                    children=None,
                    id="speed-tooltip",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Your Skill/Spell Speed stat, not your GCD.",
                    target="speed-tooltip",
                ),
            ],
            width=12,
            md=1,
            id="speed-stat-label",
        ),
        dbc.Col(
            [
                dbc.Input(
                    value=speed,
                    type="number",
                    placeholder=None,
                    id="speed-stat",
                ),
                dbc.FormFeedback(
                    f"Value must be between {stat_ranges['SPEED']['lower']} - {stat_ranges['SPEED']['upper']}. Do not enter your GCD.",
                    type="invalid",
                ),
            ]
        ),
    ]

    middle_stat_list = [
        dbc.Label("CRT:", width=12, md=1, id="crt-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=crit,
                    type="number",
                    placeholder="Critical Hit",
                    id="CRT",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['CRT']['lower']} - {stat_ranges['CRT']['upper']}",
                    type="invalid",
                ),
            ]
        ),
        dbc.Label("DH:", width=12, md=1, id="dh-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=direct_hit,
                    type="number",
                    placeholder="Direct Hit",
                    id="DH",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['DH']['lower']} - {stat_ranges['DH']['upper']}",
                    type="invalid",
                ),
            ]
        ),
        dbc.Label("WD:", width=12, md=1, id="wd-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=weapon_damage,
                    type="number",
                    placeholder="Weapon Damage",
                    id="WD",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['WD']['lower']} - {stat_ranges['WD']['upper']}",
                    type="invalid",
                ),
            ]
        ),
    ]

    bottom_stat_list = [
        dbc.Label("TEN:", width=12, md=1, id="tenacity-label"),
        dbc.Col(
            [
                dbc.Input(
                    value=tenacity,
                    type="number",
                    placeholder="Tenacity",
                    id="TEN",
                ),
                dbc.FormFeedback(
                    f"Please enter a value between {stat_ranges['TEN']['lower']} - {stat_ranges['TEN']['upper']}",
                    type="invalid",
                ),
            ],
            width=12,
            md=3,
        ),
    ]

    # Stat fields
    top_stat_row = dbc.Row(
        top_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )
    middle_stat_row = dbc.Row(
        middle_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )

    bottom_stat_row = html.Div(
        dbc.Row(bottom_stat_list, class_name="g-2", style={"padding-bottom": "15px"}),
        id="bottom-build-row",
    )

    job_build_card = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2(
                        "Player analysis",
                        className="display-3",
                        style={"font-size": "2.5em"},
                    ),
                    html.P(
                        "Analyze damage variability for a single player.",
                        className="lead",
                    ),
                    html.Hr(className="my-2"),
                    html.H3("Select a role and enter job build"),
                    html.P(
                        "A job build must be fully entered before a log can be analyzed. "
                        "You can load a build from an etro.gg / xivgear.app URL, or manually enter the values."
                    ),
                    dbc.Form(
                        [
                            job_build_input,
                            role_input,
                            xiv_gear_select,
                            html.H3("Job stats"),
                            html.P(
                                "Do not include any percent bonus to main stat, this is automatically "
                                "calculated."
                            ),
                            dbc.Row(id="job-build-name-div"),
                            top_stat_row,
                            middle_stat_row,
                            bottom_stat_row,
                            dbc.Row(id="party-bonus-warning"),
                            tincture_input,
                        ]
                    ),
                ]
            )
        )
    )

    return job_build_card


def initialize_fflogs_card(
    fflogs_url: str | None = None,
    encounter_name_time: list[str] = [],
    phase_select_options: list[dict[str, str]] = [],
    phase_select_value: int = 0,
    phase_selector_hidden: bool = True,
    job_radio_options_dict: dict[str, list[dict[str, str]]] = {
        "Tank": [],
        "Healer": [],
        "Melee": [],
        "Physical Ranged": [],
        "Magical Ranged": [],
    },
    job_radio_value_dict: dict[str, str | None] = {
        "Tank": None,
        "Healer": None,
        "Melee": None,
        "Physical Ranged": None,
        "Magical Ranged": None,
    },
    encounter_hidden: bool = True,
    analyze_hidden: bool = True,
) -> html.Div:
    """
    Create FFLogs analysis card with URL input and job selection.

    Builds a card with:
    - FFLogs URL input and validation
    - Phase selection for multi-phase fights
    - Job selection radio buttons by role
    - Analysis button

    Args:
        fflogs_url: FFLogs report URL
        encounter_name_time: List of encounter name and timestamp
        phase_select_options: Options for phase select dropdown
        phase_select_value: Selected phase value
        phase_selector_hidden: Whether to show phase selector
        job_radio_options_dict: Job options for each role's radio buttons
        job_radio_value_dict: Selected job for each role
        encounter_hidden: Whether to show encounter info
        analyze_hidden: Whether to show analyze button

    Returns:
        html.Div containing the complete FFLogs analysis card
    """
    fflogs_row = dbc.Row(
        [
            dbc.Label("Log URL", width=12, md=2),
            dbc.Col(
                [
                    dbc.Input(
                        value=fflogs_url,
                        type="text",
                        placeholder="Enter FFLogs URL",
                        id="fflogs-url",
                    ),
                    dbc.FormFeedback(type="invalid", id="fflogs-url-feedback"),
                ],
                className="me-3",
            ),
            dbc.Col(
                [
                    dbc.Button(
                        "Submit",
                        color="primary",
                        id="fflogs-url-state",
                    ),
                ],
                width="auto",
            ),
        ],
        class_name="mb-3",
        style={"padding-bottom": "15px"},
    )
    phase_select_row = html.Div(
        dbc.Row(
            children=[
                dbc.Label("Phase:", width=12, md=2, id="phase-label"),
                dbc.Col(
                    dbc.Select(
                        options=phase_select_options,
                        value=[phase_select_value],
                        id="phase-select",
                    ),
                    width=12,
                    md=5,
                ),
            ],
        ),
        id="phase-select-div",
        hidden=phase_selector_hidden,
        style={"padding-bottom": "15px"},
    )
    encounter_info = dbc.Row(
        [
            html.H4(
                [
                    html.Span("Job selection:", id="role-tooltip"),
                    dbc.Tooltip(
                        "If a supported role is greyed out, select the correct role above, enter the correct stats, and then click the Submit button for the FFLogs URL again.",
                        target="role-tooltip",
                    ),
                ],
                id="select-job",
                style={
                    "textDecoration": "underline",
                    "textDecorationStyle": "dotted",
                    "cursor": "pointer",
                },
            ),
            dbc.Label("Tanks:"),
            dbc.RadioItems(
                value=job_radio_value_dict["Tank"],
                options=job_radio_options_dict["Tank"],
                input_style={
                    "margin-bottom": "0rem",
                },
                style={
                    "margin-bottom": "0rem",
                },
                id="tank-jobs",
            ),
            dbc.Label("Healers:"),
            dbc.RadioItems(
                value=job_radio_value_dict["Healer"],
                options=job_radio_options_dict["Healer"],
                id="healer-jobs",
            ),
            dbc.Label("Melee:"),
            dbc.RadioItems(
                value=job_radio_value_dict["Melee"],
                options=job_radio_options_dict["Melee"],
                id="melee-jobs",
            ),
            dbc.Label("Physical Ranged:"),
            dbc.RadioItems(
                value=job_radio_value_dict["Physical Ranged"],
                options=job_radio_options_dict["Physical Ranged"],
                id="physical-ranged-jobs",
            ),
            dbc.Label("Magical Ranged:"),
            dbc.RadioItems(
                value=job_radio_value_dict["Magical Ranged"],
                options=job_radio_options_dict["Magical Ranged"],
                id="magical-ranged-jobs",
            ),
        ]
    )

    fflogs_card = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2("Enter log to analyze"),
                    dbc.Form(
                        [
                            fflogs_row,
                            html.H3(
                                children=encounter_name_time, id="encounter-name-time"
                            ),
                            phase_select_row,
                            html.Div(
                                [encounter_info],
                                id="encounter-info",
                                hidden=encounter_hidden,
                            ),
                        ]
                    ),
                    html.Br(),
                    html.Div(
                        [
                            dbc.Button(
                                "Analyze rotation",
                                color="primary",
                                id="compute-dmg-button",
                            )
                        ],
                        id="compute-dmg-div",
                        hidden=analyze_hidden,
                    ),
                ]
            ),
        ),
        id="fflogs-card",
    )
    return fflogs_card


def initialize_rotation_card(
    rotation_figure: Figure | None = None,
    rotation_percentile_table: dash_table.DataTable | None = None,
) -> dbc.Card:
    """
    Create card displaying rotation DPS distribution and percentiles.

    Args:
        rotation_figure: Plotly figure showing DPS distribution
        rotation_percentile_table: DataTable with DPS percentiles

    Returns:
        Card with two-column layout containing plot and table
    """
    rotation_dmg_pdf_card = dbc.Card(
        dbc.CardBody(
            [
                # Header
                html.H2("Rotation DPS distribution"),
                # Description
                html.P(
                    "The DPS distribution and your DPS is plotted below. "
                    "Your DPS and corresponding percentile is shown in green "
                    "along with select percentiles."
                ),
                html.P(
                    "The DPS distribution is also summarized by its first "
                    "three moments: mean, standard deviation, and skewness."
                ),
                # Two-column layout
                html.Div(
                    dbc.Row(
                        [
                            # Left: Plot
                            dbc.Col(
                                html.Div(
                                    children=rotation_figure, id="rotation-pdf-fig-div"
                                ),
                                width=12,
                                md=9,
                            ),
                            # Right: Table
                            dbc.Col(
                                html.Div(
                                    children=rotation_percentile_table,
                                    id="rotation-percentile-div",
                                ),
                                align="center",
                            ),
                        ]
                    )
                ),
            ],
            className="mb-3",
        ),
    )
    return rotation_dmg_pdf_card


def initialize_action_card(
    action_figure: Figure | None = None,
    action_summary_table: dash_table.DataTable | None = None,
    action_options: list[dict] = [],
    action_values: list[str] = [],
) -> dbc.Card:
    """
    Create card showing DPS distributions for individual actions.

    Args:
        action_figure: Plotly figure with action DPS distributions
        action_summary_table: DataTable with action DPS summary stats
        action_options: Options for action selector dropdown
        action_values: Initially selected actions

    Returns:
        Card containing plot, action selector, and summary table
    """
    action_dmg_pdf_card = dbc.Card(
        dbc.CardBody(
            [
                html.H2("Action DPS distributions"),
                html.P(
                    "The DPS distribution for each action is shown below. "
                    "Hover over the graph to see the controls and change the view, "
                    "or use the dropdown below to remove/add actions."
                ),
                html.P(
                    "The table below shows DPS at the 50th percentile, your actual DPS, "
                    "and the corresponding percentile."
                ),
                html.Div(children=action_figure, id="action-pdf-fig-div"),
                html.Div(
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Dropdown(
                                    options=action_options,
                                    value=action_values,
                                    multi=True,
                                    id="action-dropdown",
                                ),
                                width=11,
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        html.I(
                                            className="fa-solid fa-rotate-left",
                                            id="action-reset",
                                        ),
                                    )
                                ],
                                align="center",
                            ),
                        ]
                    )
                ),
                html.Br(),
                html.Div(children=action_summary_table, id="action-summary-table-div"),
            ],
            className="mb-3",
        ),
    )
    return action_dmg_pdf_card


def initialize_new_action_card(action_figure: Figure | None = None) -> dbc.Card:
    """
    Create card showing box plots of action DPS distributions.

    Args:
        action_figure: Plotly figure with box plots for each action's DPS

    Returns:
        Card containing plot and descriptions
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.H2("Action DPS distributions"),
                html.P(
                    "The DPS distribution for each action is shown below as box and whisker "
                    "plots. Whiskers represent the 10th and 90th percentiles, respectively. "
                    "Hover over a box plot to see the corresponding percentile, along with "
                    "select other percentiles."
                ),
                html.P(
                    "Note: reported DoT DPS values from FFLogs might be underestimated "
                    "compared to the computed DPS distributions. This is a known issue with "
                    "currently no fix because of how DoT damage information is conveyed via ACT."
                ),
                html.Div(children=action_figure, id="action-pdf-fig-div"),
            ],
            className="mb-3",
        ),
    )


def initialize_results(
    player_name: str | None = None,
    crit_text: str | None = None,
    job_alert: list[html.Div] = [],
    rotation_card: list[html.Div] = [],
    action_card: list[html.Div] = [],
    analysis_url: str | None = None,
    xiv_analysis_url: str | None = None,
    results_hidden: bool = True,
) -> html.Div:
    """
    Create results card showing analysis outcome and details.

    Args:
        player_name: Player name for header
        crit_text: Crit analysis result text
        job_alert: Job specific alerts/warnings
        rotation_card: Rotation analysis card
        action_card: Action analysis card
        analysis_url: URL to share analysis
        xiv_analysis_url: URL for XIVAnalysis
        results_hidden: Whether to show results

    Returns:
        Card containing complete analysis results
    """
    player_name = (
        f"{player_name}, your crit was..." if player_name else "Your crit was..."
    )

    crit_results = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    # Header
                    html.H2(player_name),
                    # Results content
                    html.Div(
                        [
                            # Crit result and explanation
                            dbc.Row(
                                [
                                    html.P(children=crit_text, id="crit-result-text"),
                                    html.Br(),
                                    html.A(
                                        "Click here for an explanation on the consequences of this.",
                                        href="#",
                                        id="result-interpretation-open",
                                    ),
                                ]
                            ),
                            html.Br(),
                            # Job alerts
                            dbc.Row(html.Div(children=job_alert, id="job-alert-id")),
                            html.Br(),
                            # Analysis links
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
                                            id="analysis-link",
                                        ),
                                        width=9,
                                        align="center",
                                    ),
                                    dbc.Col(
                                        dcc.Clipboard(
                                            id="clipboard",
                                            style={"display": "inline-block"},
                                        ),
                                        align="center",
                                        width=1,
                                    ),
                                ]
                            ),
                            html.Br(),
                            # XIVAnalysis link
                            dbc.Row(
                                [
                                    html.A(
                                        [
                                            "Analyze rotation in xivanalysis ",
                                            html.I(
                                                className="fas fa-external-link-alt",
                                                style={"font-size": "0.8em"},
                                            ),
                                        ],
                                        href=xiv_analysis_url,
                                        target="_blank",
                                    ),
                                ]
                            ),
                            html.Br(),
                            # Modal
                            dbc.Modal(
                                [
                                    dbc.ModalHeader(
                                        dbc.ModalTitle(
                                            "Consequences of raw DPS and its percentiles for this analysis"
                                        )
                                    ),
                                    dbc.ModalBody(
                                        html.P(
                                            [
                                                "The percentile reported is the percentile of the damage distribution, which depends on the rotation, kill time, party composition, job build, etc. Percentiles from FFLogs are more complicated because DPS percentiles are computed across kills with many different damage distributions. This can be due to different rotations (including GCDs lost to healing, raising, movement, chadding, etc), different job builds, non-BiS gear, party compositions, and kill times. Percentiles from FFLogs are also only computed for derived DPS metrics like ",
                                                html.A(
                                                    "rDPS and aDPS.",
                                                    href="https://www.fflogs.com/help/rdps",
                                                    target="_blank",
                                                ),
                                                html.Br(),
                                                html.Br(),
                                                'This analysis is affected by party composition and any external buffs present because raw DPS is used. Party compositions with many buffs will naturally have higher damage distributions across all jobs compared to a party composition few buffs. For "rDPS jobs" like Scholar or Astrologian, party contributions to their buffs can lead to a significant difference between DPS and rDPS, and are not captured by this analysis. For "aDPS jobs" like White Mage and Sage, raw DPS is aDPS and can indicate how well a person played into raid buffs for a run.',
                                            ]
                                        )
                                    ),
                                    dbc.ModalFooter(
                                        dbc.Button(
                                            "Close",
                                            id="result-interpretation-close",
                                            className="ms-auto",
                                            n_clicks=0,
                                        )
                                    ),
                                ],
                                id="result-interpretation-modal",
                                is_open=False,
                                size="lg",
                            ),
                        ],
                        id="crit-result-div",
                    ),
                    # Analysis results
                    rotation_card,
                    html.Br(),
                    action_card,
                ]
            )
        ),
        id="results-div",
        hidden=results_hidden,
    )
    return crit_results
