"""
Create cards used to display content.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def initialize_job_build(
    etro_url=None,
    role="Healer",
    main_stat=None,
    secondary_stat=None,
    determination=None,
    speed=None,
    crit=None,
    direct_hit=None,
    weapon_damage=None,
    delay=None,
    party_bonus=1.05,
    medication_amt=351,
):
    """
    Create the job build div, optionally setting initial values for them.
    Initial values are set when an `analysis_id` is present in the URL.
    Callback decorators require an input to trigger them, which isn't possible
    to automatically trigger them just once.
    There doesn't seem to be a way to set/edit values without a callback except when
    the element is created.
    """

    etro_input = dbc.Row(
        [
            dbc.Label("Etro build URL", width=12, md=2),
            dbc.Col(
                [
                    dbc.Input(
                        value=etro_url,
                        type="text",
                        placeholder="Enter Etro job build URL",
                        id="etro-url",
                    ),
                    dbc.FormFeedback(
                        type="invalid",
                        id="etro-url-feedback",
                    ),
                ],
                className="me-3",
            ),
            dbc.Col(
                dbc.Button(
                    "Submit",
                    color="primary",
                    id="etro-url-button",
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
                        "Medication/potion. If no medication was used, " "keep the default value selected.",
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
                            {
                                "label": "Grade 1 Gemdraught (+361)",
                                "value": 351
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
        ]
    )

    top_stat_list = [
        dbc.Label(children=None, width=12, md=1, id="main-stat-label"),
        dbc.Col(
            dbc.Input(
                value=main_stat,
                type="number",
                placeholder=None,
                min=100,
                max=6000,
                id="main-stat",
            )
        ),
        dbc.Label(children=None, width=12, md=1, id="secondary-stat-label"),
        dbc.Col(
            dbc.Input(
                value=secondary_stat,
                type="number",
                placeholder=None,
                min=100,
                max=5000,
                id="secondary-stat",
            )
        ),
        dbc.Label(children="DET:", width=12, md=1, id="det-label"),
        dbc.Col(
            dbc.Input(
                value=determination,
                type="number",
                placeholder="Determination",
                min=100,
                max=5000,
                id="DET",
            )
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
                dbc.FormFeedback(
                    "Please enter your Skill/Spell Speed stat, not GCD.",
                    type="invalid",
                    id="speed-feedback",
                ),
            ],
            width=12,
            md=1,
            id="speed-stat-label",
        ),
        dbc.Col(
            dbc.Input(
                value=speed,
                type="number",
                placeholder=None,
                min=100,
                max=5000,
                id="speed-stat",
            )
        ),
    ]

    bottom_stat_list = [
        dbc.Label("CRT:", width=12, md=1, id="crt-label"),
        dbc.Col(
            dbc.Input(
                value=crit,
                type="number",
                placeholder="Critical Hit",
                min=100,
                max=5000,
                id="CRT",
            )
        ),
        dbc.Label("DH:", width=12, md=1, id="dh-label"),
        dbc.Col(
            dbc.Input(
                value=direct_hit,
                type="number",
                placeholder="Direct Hit",
                min=100,
                max=5000,
                id="DH",
            )
        ),
        dbc.Label("WD:", width=12, md=1, id="wd-label"),
        dbc.Col(
            dbc.Input(
                value=weapon_damage,
                type="number",
                placeholder="Weapon Damage",
                min=100,
                max=500,
                id="WD",
            )
        ),
        dbc.Label(
            [
                html.Span(
                    "DEL:",
                    id="del-tooltip",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Delay, under weapon stats, for auto-attacks. "
                    "Should be a value like 3.44.",
                    target="del-tooltip",
                ),
            ],
            width=12,
            md=1,
            id="delay-label",
        ),
        dbc.Col(
            dbc.Input(
                value=delay,
                type="number",
                placeholder="Delay",
                min=1.0,
                max=4.0,
                id="DEL",
            )
        ),
    ]

    # Stat fields
    top_stat_row = dbc.Row(
        top_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )
    bottom_stat_row = dbc.Row(
        bottom_stat_list, class_name="g-2", style={"padding-bottom": "15px"}
    )

    # Party bonus/pot
    party_bonus = dbc.Row(
        [
            # Party bonus
            dbc.Col(
                html.Div(
                    [
                        dbc.Label(
                            [
                                html.Span(
                                    r"Add % bonus to main stat",
                                    id="bonus-tooltip",
                                    style={
                                        "textDecoration": "underline",
                                        "textDecorationStyle": "dotted",
                                        "cursor": "pointer",
                                    },
                                ),
                                dbc.Tooltip(
                                    r"The % bonus added to main stat for each unique job present. For most cases, this should be 5%. If a job like Physical Ranged is missing, this value should be 4%.",
                                    target="bonus-tooltip",
                                ),
                            ],
                            # width=1,
                        ),
                        dcc.Slider(
                            1.00,
                            1.05,
                            step=0.01,
                            value=party_bonus,
                            marks={
                                1.00: "0%",
                                1.01: "1%",
                                1.02: "2%",
                                1.03: "3%",
                                1.04: "4%",
                                1.05: "5%",
                            },
                            id="main-stat-slider",
                        ),
                    ]
                ),
                md=4,
                width=12,
            ),
            # Medication
            # dbc.Col(
            #     [
            #         dbc.Label(
            #             [
            #                 html.Span(
            #                     "Tincture grade",
            #                     id="tincture-tooltip",
            #                     style={
            #                         "textDecoration": "underline",
            #                         "textDecorationStyle": "dotted",
            #                         "cursor": "pointer",
            #                     },
            #                 ),
            #                 dbc.Tooltip(
            #                     "If no tincture was used, "
            #                     "keep the default value selected.",
            #                     target="tincture-tooltip",
            #                 ),
            #             ],
            #         ),
            #         dbc.Select(
            #             name="Tincture grade",
            #             id="tincture-grade",
            #             options=[
            #                 {
            #                     "label": "Grade 8 Tincture (+262)",
            #                     "value": 262,
            #                 },
            #                 {
            #                     "label": "Grade 7 Tincture (+223)",
            #                     "value": 223,
            #                 },
            #             ],
            #             value=medication_amt,
            #         ),
            #     ]
            # ),
        ]
    )

    job_build_card = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2("Select a role and enter job build"),
                    html.P(
                        "A job build must be fully entered before a log can be analyzed. A build from an Etro URL can be loaded in or values can be manually entered. A role must be selected so the correct main/secondary stats can be used. If an Etro build is used, the role will be automatically selected. Do not include any percent bonus to main stat, this is automatically calculated."
                    ),
                    dbc.Form(
                        [
                            etro_input,
                            role_input,
                            html.H3("Job stats"),
                            dbc.Row(id="etro-build-name-div"),
                            top_stat_row,
                            bottom_stat_row,
                            dbc.Row(id="party-bonus-warning"),
                            tincture_input,
                            # party_bonus,
                        ]
                    ),
                ]
            )
        )
    )

    return job_build_card


# FIXME: Handle loading in
def initialize_fflogs_card(
    fflogs_url=None,
    encounter_info=[],
    job_radio_options_dict={
        "Tank": [],
        "Healer": [],
        "Melee": [],
        "Physical Ranged": [],
        "Magical Ranged": [],
    },
    job_radio_value_dict={
        "Tank": None,
        "Healer": None,
        "Melee": None,
        "Physical Ranged": None,
        "Magical Ranged": None,
    },
    encounter_hidden=True,
    analyze_hidden=True,
):
    fflogs_url = dbc.Row(
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

    encounter_info = dbc.Row(
        [
            html.H3(children=encounter_info, id="read-fflogs-url"),
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
                            fflogs_url,
                            html.Div(
                                encounter_info,
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


def initialize_rotation_card(rotation_figure=None, rotation_percentile_table=None):
    rotation_dmg_pdf_card = dbc.Card(
        dbc.CardBody(
            [
                html.H2("Rotation DPS distribution"),
                html.P(
                    "The DPS distribution and your DPS is plotted below. Your DPS and corresponding percentile is shown in green along with select percentiles."
                ),
                html.P(
                    "The DPS distribution is also summarized by its first three moments: mean, standard deviation, and skewness."
                ),
                html.Div(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    children=rotation_figure, id="rotation-pdf-fig-div"
                                ),
                                width=12,
                                md=9,
                            ),
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
    action_figure=None, action_summary_table=None, action_options=[], action_values=[]
):
    action_dmg_pdf_card = dbc.Card(
        dbc.CardBody(
            [
                html.H2("Action DPS distributions"),
                html.P(
                    "The DPS distribution for each action is shown below. Hover over the graph to see the controls and change the view, or use the dropdown below to remove/add actions."
                ),
                html.P(
                    "The table below shows DPS at the 50th percentile, your actual DPS, and the corresponding percentile."
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


def initialize_results(
    player_name=None,
    crit_text=None,
    job_alert=[],
    rotation_card=[],
    action_card=[],
    analysis_url=None,
    results_hidden=True,
):
    if player_name is not None:
        player_name = f"{player_name}, your crit was..."
    else:
        player_name = "Your crit was..."
    crit_results = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2(player_name),
                    html.Div(
                        [
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
                            dbc.Row(html.Div(children=job_alert, id="job-alert-id")),
                            html.Br(),
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
                    # html.Br(),
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
