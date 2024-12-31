import pickle
import time
from typing import Optional, Tuple
from uuid import uuid4

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    callback,
    dcc,
    html,
)
from dash.exceptions import PreventUpdate
from plotly.graph_objs._figure import Figure

from crit_app.api_queries import (
    get_encounter_job_info,
    headers,
    limit_break_damage_events,
    parse_etro_url,
    parse_fflogs_url,
)

# from app import app
from crit_app.config import BLOB_URI, DRY_RUN
from crit_app.dmg_distribution import (
    PartyRotation,
    SplitPartyRotation,
    job_analysis_to_data_class,
    rotation_dps_pdf,
    unconvovle_clipped_pdf,
)
from crit_app.figures import (
    make_action_box_and_whisker_figure,
    make_kill_time_graph,
    make_party_rotation_pdf_figure,
    make_rotation_pdf_figure,
)
from crit_app.job_data.encounter_data import (
    encounter_level,
    valid_encounters,
)
from crit_app.job_data.job_data import caster_healer_strength, weapon_delays
from crit_app.job_data.roles import abbreviated_job_map, role_mapping, role_stat_dict
from crit_app.party_cards import (
    create_fflogs_card,
    create_party_accordion,
    create_quick_build_div,
    create_quick_build_table,
    create_tincture_input,
    party_analysis_assumptions_modal,
)
from crit_app.shared_elements import (
    check_prior_job_analyses,
    check_prior_party_analysis,
    etro_build,
    format_kill_time_str,
    read_encounter_table,
    read_party_report_table,
    read_report_table,
    rotation_analysis,
    unflag_party_report_recompute,
    unflag_redo_rotation,
    unflag_report_recompute,
    update_encounter_table,
    update_party_report_table,
    update_report_table,
    validate_meldable_stat,
    validate_secondary_stat,
    validate_speed_stat,
    validate_weapon_damage,
)
from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable

reverse_abbreviated_role_map = dict(
    zip(abbreviated_job_map.values(), abbreviated_job_map.keys())
)

app = dash.get_app()
dash.register_page(
    __name__,
    path_template="/party_analysis/<party_analysis_id>",
    path="/party_analysis",
)


def layout(party_analysis_id=None):
    if party_analysis_id is None:
        fflogs_card = create_fflogs_card()
        return dash.html.Div(
            [
                fflogs_card,
            ]
        )

    else:
        # Read in everything:
        try:
            with open(
                BLOB_URI / "party-analyses" / f"party-analysis-{party_analysis_id}.pkl",
                "rb",
            ) as f:
                party_analysis_obj = pickle.load(f)
        except Exception:
            return html.Div(
                [
                    html.H2("404 Not Found"),
                    html.P(
                        [
                            "The link entered does not exist. ",
                            html.A("Click here", href="/party_analysis"),
                            " to return home and analyze a rotation.",
                        ]
                    ),
                ]
            )

        # Party level analysis,
        party_report_df = read_party_report_table()
        party_report_df = party_report_df[
            party_report_df["party_analysis_id"] == party_analysis_id
        ]
        # Encounters, filtered to fight
        encounter_df = read_encounter_table()
        encounter_df = party_report_df[["report_id", "fight_id"]].merge(
            encounter_df, on=["report_id", "fight_id"], how="inner"
        )

        # job level analysis, filtered to fight
        job_report_df = read_report_table()
        job_report_df = party_report_df[["report_id", "fight_id"]].merge(
            job_report_df, on=["report_id", "fight_id"], how="inner"
        )

        encounter_id, kill_time = party_report_df.merge(
            encounter_df, on=["report_id", "fight_id"]
        )[["encounter_id", "kill_time"]].iloc[0]

        job_information = encounter_df.merge(
            job_report_df,
            on=["report_id", "fight_id", "player_name", "job"],
            how="inner",
        )

        # Filter down to jobs in this party analysis
        # A job in a fight might get analyzed with different builds
        job_analysis_ids = (
            party_report_df[[f"analysis_id_{x+1}" for x in range(8)]].iloc[0].to_list()
        )
        job_information = job_information[
            job_information["analysis_id"].isin(job_analysis_ids)
        ]
        # Drop duplicate rows
        # Don't use pet IDs as a unique identifier because it's a list
        job_information = job_information.drop_duplicates(
            subset=job_information.drop(columns=["pet_ids"]).columns
        )

        ############################
        ### FFLogs Card Elements ###
        ############################

        job_information = sorted(
            job_information[
                [
                    "role",
                    "job",
                    "player_name",
                    "player_id",
                    "main_stat_pre_bonus",
                    "secondary_stat_pre_bonus",
                    "determination",
                    "speed",
                    "critical_hit",
                    "direct_hit",
                    "weapon_damage",
                    "delay",
                    "etro_id",
                    "medication_amount",
                ]
            ].to_dict(orient="records"),
            key=lambda d: (d["job"], d["player_name"], d["player_id"]),
        )

        medication_amount = job_information[0]["medication_amount"]
        party_accordion = create_party_accordion(job_information, True)

        kill_time_str = format_kill_time_str(kill_time)
        encounter_name = encounter_df["encounter_name"].iloc[0]
        encounter_info = [
            html.P(
                [
                    html.Span(encounter_name, id="encounter-name"),
                    " (",
                    html.Span(kill_time_str),
                    ")",
                ]
            )
        ]

        quick_build_div = create_quick_build_div(
            create_quick_build_table(job_information)
        )

        buttons = html.Div(
            [
                dbc.Button(
                    "Validate builds (click to show analyze button)",
                    id="etro-validate",
                    class_name="me-1 w-100",
                ),
                html.Div(
                    [
                        dbc.Button(
                            "Analyze party rotation",
                            id="party-compute",
                            class_name="w-100",
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

        collapse_button = dbc.Button(
            children="Show party build",
            n_clicks=0,
            id="party-collapse-button",
            class_name="mb-3",
        )

        encounter_children = [
            html.H3(children=encounter_info, id="read-fflogs-url2"),
            collapse_button,
            dbc.Collapse(
                [
                    html.H3("Enter job builds"),
                    html.P(
                        "Job builds for all players must be entered. Either enter the Etro link or input each job's stats. Do not include any party composition bonuses to the main stat, this is automatically calculated."
                    ),
                    create_tincture_input(medication_amount),
                    quick_build_div,
                    party_accordion,
                    buttons,
                    html.H4("Analysis progress: Done!", id="party-progress-header"),
                    dbc.Progress(
                        value=100,
                        style={"height": "25px"},
                        color="#009670",
                        id="party-progress",
                        class_name="me-1",
                    ),
                    html.P(id="party-progress-job"),
                ],
                id="party-list-collapse",
                is_open=False,
                class_name="me-1",
            ),
        ]

        report_id, fight_id = party_report_df[["report_id", "fight_id"]].iloc[0]
        fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"
        fflogs_card = create_fflogs_card(fflogs_url, encounter_children)

        #############################
        ### Results Card elements ###
        #############################

        analysis_url = (
            f"https://howbadwasmycritinxiv.com/party_analysis/{party_analysis_id}"
        )
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
                    dcc.Graph(
                        figure=make_party_rotation_pdf_figure(party_analysis_obj)
                    ),
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
                            dcc.Graph(
                                figure=make_kill_time_graph(
                                    party_analysis_obj, kill_time
                                )
                            ),
                        ]
                    )
                )
            )
        )

        # Job-level view
        job_selector = party_report_df[["report_id", "fight_id"]].merge(
            job_report_df, on=["report_id", "fight_id"]
        )[["job", "player_name", "analysis_id"]]

        # Filter down to job analyses only in the party analysis.
        job_selector = (
            job_selector[job_selector["analysis_id"].isin(job_analysis_ids)]
            .to_numpy()
            .tolist()
        )
        job_selector_options = [
            {
                "label": html.Span(
                    [
                        html.Span(
                            abbreviated_job_map[x[0]],
                            style={
                                "font-family": "job-icons",
                                "font-size": "1.2em",
                                "position": "relative",
                                "top": "3px",
                                "color": "#FFFFFF",
                            },
                        ),
                        html.Span(" " + x[1], style={"color": "#FFFFFF"}),
                    ],
                    style={"align-items": "center", "justify-content": "center"},
                ),
                "value": x[2],
            }
            for x in job_selector
        ]

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
                    job_selector_options,
                    value=job_selector[0][2],
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
        return html.Div(
            [
                fflogs_card,
                html.Br(),
                dbc.Card(
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
                ),
            ]
        )

@callback(
    Output("job-rotation-pdf", "figure"),
    Input("job-selector", "value"),
    Input("job-graph-type", "value"),
)
def load_job_rotation_figure(job_analysis_id: Optional[str], graph_type: str) -> Figure:
    """
    Load and create job rotation figure based on analysis data.

    Args:
        job_analysis_id: Analysis ID to load data for
        graph_type: Type of graph to create ('rotation' or 'action')

    Returns:
        Plotly figure showing either rotation PDF or action box plots

    Raises:
        PreventUpdate: If job_analysis_id not provided
        FileNotFoundError: If analysis data files missing
        ValueError: If invalid graph type specified
    """
    if job_analysis_id is None:
        raise PreventUpdate
    with open(BLOB_URI / f"job-analysis-data-{job_analysis_id}.pkl", "rb") as f:
        job_object = pickle.load(f)

    with open(BLOB_URI / f"rotation-object-{job_analysis_id}.pkl", "rb") as f:
        rotation_object = pickle.load(f)

    actions_df = rotation_object.actions_df

    action_dps = (
        actions_df[["ability_name", "amount"]].groupby("ability_name").sum()
        / job_object.active_dps_t
    ).reset_index()
    rotation_dps = action_dps["amount"].sum()

    if graph_type == "rotation":
        return make_rotation_pdf_figure(
            job_object, rotation_dps, job_object.active_dps_t, job_object.analysis_t
        )
    else:
        return make_action_box_and_whisker_figure(
            job_object, action_dps, job_object.active_dps_t, job_object.analysis_t
        )


@callback(Output("job-level-analysis", "href"), Input("job-selector", "value"))
def job_analysis_redirect(job_analysis_id: Optional[str]) -> str:
    """
    Redirect to individual analysis URL.

    Args:
        job_analysis_id: analysis ID to link to

    Returns:
        URL path string for job analysis page
    """
    return f"/analysis/{job_analysis_id}"


@callback(
    Output("party-list-collapse", "is_open"),
    Output("party-collapse-button", "children"),
    Input("party-collapse-button", "n_clicks"),
)
def toggle_party_list(n_clicks: Optional[int]) -> Tuple[bool, str]:
    """
    Toggle party list visibility and update button text.

    Args:
        n_clicks: Number of times button has been clicked

    Returns:
        Tuple containing:
            - Boolean for if list should be visible
            - String for button text
    """
    if n_clicks % 2 == 1:
        return True, "Click to hide party list"
    else:
        return False, "Click to show party list"


@callback(
    Output({"type": "etro-input", "index": ALL}, "value"),
    Input("quick-build-fill-button", "n_clicks"),
    State("quick-build-table", "data"),
    prevent_initial_call=True,
)
def quick_fill_job_build(n_clicks, etro_links):
    return [e["etro_link"] for e in etro_links]


@callback(
    Output("party-clipboard", "content"),
    Input("party-clipboard", "n_clicks"),
    State("party-analysis-link", "value"),
)
def copy_party_analysis_link(n, selected):
    """Copy analysis link to clipboard."""
    if selected is None:
        raise PreventUpdate
    return selected


@callback(
    Output("fflogs-url-feedback2", "children"),
    Output("fflogs-url2", "valid"),
    Output("fflogs-url2", "invalid"),
    Output("encounter-info", "children"),
    Input("fflogs-url-state2", "n_clicks"),
    State("fflogs-url2", "value"),
    prevent_initial_call=True,
)
def party_fflogs_process(n_clicks, url):
    if url is None:
        raise PreventUpdate

    invalid_return = [False, True, []]

    report_id, fight_id, error_code = parse_fflogs_url(url)

    if error_code == 1:
        return "This link isn't FFLogs...", []
    elif error_code == 2:
        return tuple(
            [
                """Please enter a log linked to a specific kill.\nfight=last in the URL is also currently unsupported."""
            ]
            + invalid_return
        )
    elif error_code == 3:
        return tuple(["Invalid report ID."] + invalid_return)
    (
        encounter_id,
        start_time,
        job_information,
        limit_break_information,
        kill_time,
        encounter_name,
        report_start_time,
        furthest_index_phase,
        r,
    ) = get_encounter_job_info(report_id, int(fight_id))

    if encounter_id not in valid_encounters:
        return tuple(
            [f"Sorry, {encounter_name} is currently not supported."] + invalid_return
        )

    kill_time_str = format_kill_time_str(kill_time)

    encounter_info = [
        html.P(
            [
                html.Span(encounter_name, id="encounter-name"),
                " (",
                html.Span(kill_time_str),
                ")",
            ]
        ),
        html.P(""),
    ]

    # Sort by job, player name so the order will always be the same
    job_information = sorted(
        job_information, key=lambda d: (d["job"], d["player_name"], d["player_id"])
    )

    quick_build_table = create_quick_build_table(job_information)
    quick_build_div = create_quick_build_div(quick_build_table)

    party_accordion = create_party_accordion(job_information)

    buttons = html.Div(
        [
            dbc.Button(
                "Validate builds (click to show analyze button)",
                id="etro-validate",
                class_name="me-1 w-100",
            ),
            html.Div(
                [
                    dbc.Button(
                        "Analyze party rotation", id="party-compute", class_name="w-100"
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

    encounter_children = [
        html.H3(children=encounter_info, id="read-fflogs-url2"),
        html.H3("Enter job builds"),
        html.P(
            "Job builds for all players must be entered. Either enter the Etro link or input each job's stats. Do not include any party composition bonuses to the main stat."
        ),
        create_tincture_input(),
        quick_build_div,
        party_accordion,
        buttons,
        html.H4(id="party-progress-header"),
        dbc.Progress(
            value=0, style={"height": "25px"}, color="#009670", id="party-progress"
        ),
        html.P(id="party-progress-job"),
    ]

    if not DRY_RUN:
        db_rows = [
            (
                report_id,
                fight_id,
                encounter_id,
                furthest_index_phase,
                encounter_name,
                kill_time,
                k["player_name"],
                k["player_server"],
                k["player_id"],
                k["pet_ids"],
                k["job"],
                k["role"],
            )
            for k in job_information + limit_break_information
        ]
        update_encounter_table(db_rows)
    return (
        [],
        True,
        False,
        encounter_children,
    )


@callback(
    Output({"type": "tenacity-row", "index": MATCH}, "hidden"),
    Input({"type": "main-stat-label", "index": MATCH}, "children"),
)
def hide_non_tank_tenactiy(main_stat_label) -> bool:
    """Hide the Tenacity form for non-tanks.

    Args:
        main_stat_label (str): Main stat label used to determine role.

    Returns:
        bool: Whether to hide tenacity row.
    """
    if main_stat_label == "STR:":
        return False
    else:
        return True


@callback(
    Output({"type": "main-stat", "index": MATCH}, "value"),
    Output({"type": "TEN", "index": MATCH}, "value"),
    Output({"type": "DET", "index": MATCH}, "value"),
    Output({"type": "speed-stat", "index": MATCH}, "value"),
    Output({"type": "CRT", "index": MATCH}, "value"),
    Output({"type": "DH", "index": MATCH}, "value"),
    Output({"type": "WD", "index": MATCH}, "value"),
    Output({"type": "build-name", "index": MATCH}, "children"),
    Output({"type": "etro-input", "index": MATCH}, "valid"),
    Output({"type": "etro-input", "index": MATCH}, "invalid"),
    Output({"type": "etro-feedback", "index": MATCH}, "children"),
    Input("etro-validate", "n_clicks"),
    State({"type": "etro-input", "index": MATCH}, "value"),
    State({"type": "main-stat-label", "index": MATCH}, "children"),
    State({"type": "main-stat", "index": MATCH}, "value"),
    State({"type": "TEN", "index": MATCH}, "value"),
    State({"type": "DET", "index": MATCH}, "value"),
    State({"type": "speed-stat", "index": MATCH}, "value"),
    State({"type": "CRT", "index": MATCH}, "value"),
    State({"type": "DH", "index": MATCH}, "value"),
    State({"type": "WD", "index": MATCH}, "value"),
)
def etro_process(
    n_clicks,
    url,
    main_stat_label,
    main_stat,
    secondary_stat,
    determination,
    speed,
    critical_hit,
    direct_hit,
    weapon_damage,
):
    if n_clicks is None:
        raise PreventUpdate
    print(main_stat_label)

    if main_stat_label == "STR:":
        role = "Tank"
    elif main_stat_label == "MND:":
        role = "Healer"
    elif main_stat_label == "STR/DEX:":
        role = "Melee"
    elif main_stat_label == "DEX:":
        role = "Physical Ranged"
    elif main_stat_label == "INT:":
        role = "Magical Ranged"

    feedback = []
    invalid_return = [
        main_stat,
        secondary_stat,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        [],
        False,
        True,
    ]

    gearset_id, error_code = parse_etro_url(url)

    if error_code == 0:
        (
            etro_call_successful,
            etro_error,
            build_name,
            build_role,
            primary_stat,
            secondary_stat,
            determination,
            speed,
            critical_hit,
            direct_hit,
            weapon_damage,
            delay,
            etro_party_bonus,
        ) = etro_build(gearset_id)

        if etro_call_successful:
            # If a party bonus is applied in etro, undo it.
            if etro_party_bonus > 1:
                primary_stat = int(primary_stat / etro_party_bonus)
                # Undo STR for healer/caster
                if build_role in ("Healer", "Magical Ranged"):
                    secondary_stat = int(secondary_stat / etro_party_bonus)

            time.sleep(1)
            return (
                primary_stat,
                secondary_stat,
                determination,
                speed,
                critical_hit,
                direct_hit,
                weapon_damage,
                f"Build name: {build_name}",
                True,
                False,
                [],
            )

    # Manual validation if no url is provided/etro fails
    # All stats present
    # If role is tank/healer/caster, secondary stat is also present
    # if url is None:
    (
        main_stat,
        secondary_stat,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
    ) = invalid_return[0:7]
    secondary_stat_condition = ((role in ("Tank")) & (secondary_stat is not None)) or (
        role in ("Melee", "Physical Ranged", "Healer", "Magical Ranged")
    )
    if (
        all(
            [
                main_stat is not None,
                determination is not None,
                speed is not None,
                critical_hit is not None,
                direct_hit is not None,
                weapon_damage is not None,
            ]
        )
        & secondary_stat_condition
    ):
        # Validate each stat
        validation = [
            validate_meldable_stat("Main stat", main_stat),
            validate_secondary_stat(role, secondary_stat),
            validate_meldable_stat("Determination", determination),
            validate_speed_stat(speed),
            validate_meldable_stat("Critical hit", critical_hit),
            validate_meldable_stat("Direct hit rate", direct_hit),
            validate_weapon_damage(weapon_damage),
        ]
        if all([v[0] for v in validation]):
            return (
                main_stat,
                secondary_stat,
                determination,
                speed,
                critical_hit,
                direct_hit,
                weapon_damage,
                [],
                True,
                False,
                [],
            )

        else:
            feedback = " ".join([v[1] for v in validation if v[1] is not None])
            invalid_return.append(feedback)
            return tuple(invalid_return)

    # Non-etro link
    elif error_code == 1:
        feedback = "This isn't an etro.gg link..."
        invalid_return.append(feedback)
        return tuple(invalid_return)

    # Etro link but not to a gearset
    elif error_code == 2:
        feedback = (
            "This doesn't appear to be a valid gearset. Please double check the link."
        )
        invalid_return.append(feedback)
        return tuple(invalid_return)

    # Etro link error, usualy 404
    if not etro_call_successful:
        invalid_return.append(etro_error)
        return tuple(invalid_return)

    # Make sure correct build is used
    if build_role != role:
        feedback = f"A non-{role} etro build was used."
        invalid_return.append(feedback)
        return tuple(invalid_return)


@callback(
    Output("party-compute-div", "hidden"),
    Input({"type": "etro-input", "index": ALL}, "valid"),
    Input({"type": "etro-input", "index": ALL}, "invalid"),
)
def validate_job_builds(etro_input_valid, etro_input_invalid):
    if (not any(etro_input_invalid)) & (all(etro_input_valid)):
        return False
    else:
        return True


def job_progress(job_list, active_job):
    active_style = {
        "font-family": "job-icons",
        "font-size": "1.2em",
        "position": "relative",
        "top": "4px",
        "font-weight": "500",
        "color": "#009670",
    }
    inactive_style = {
        "font-family": "job-icons",
        "font-size": "1.2em",
        "position": "relative",
        "top": "4px",
    }

    current_job = [
        html.Span([j, " "], style=inactive_style)
        if j != active_job
        else html.Span([j, " "], style=active_style)
        for j in job_list
    ]

    return ["Analysis progress: "] + current_job


@app.long_callback(
    Output("url", "href", allow_duplicate=True),
    Input("party-compute", "n_clicks"),
    State({"type": "job-name", "index": ALL}, "children"),
    State({"type": "player-id", "index": ALL}, "children"),
    State({"type": "main-stat", "index": ALL}, "value"),
    State({"type": "TEN", "index": ALL}, "value"),
    State({"type": "DET", "index": ALL}, "value"),
    State({"type": "speed-stat", "index": ALL}, "value"),
    State({"type": "CRT", "index": ALL}, "value"),
    State({"type": "DH", "index": ALL}, "value"),
    State({"type": "WD", "index": ALL}, "value"),
    State({"type": "main-stat-label", "index": ALL}, "children"),
    State({"type": "player-name", "index": ALL}, "children"),
    State({"type": "etro-input", "index": ALL}, "value"),
    State("party-tincture-grade", "value"),
    State("encounter-name", "children"),
    State("fflogs-url2", "value"),
    running=[(Output("party-compute", "disabled"), True, False)],
    progress=[
        Output("party-progress", "value"),
        Output("party-progress", "max"),
        Output("party-progress-header", "children"),
    ],
    prevent_initial_call=True,
)
def analyze_party_rotation(
    set_progress,
    n_clicks,
    job,
    player_id,
    main_stat_no_buff,
    secondary_stat_no_buff,
    determination,
    speed,
    crit,
    dh,
    weapon_damage,
    # delay,
    main_stat_label,
    player_name,
    etro_url,
    medication_amt,
    encounter_name,
    fflogs_url,
):
    """
    Analyze and compute the damage distribution of a whole party.

    This is done by
    computing the damage distribution of each job and convolving each one together.

    The likelihood of faster kill times is also analyzed, by computing the percentile
    of the damage distribution >= Boss HP when the each job's rotation is shortened by
    2.5, 5.0, 7.5, and 10.0 seconds.

    Notation:

    party rotation = (truncated party rotation) + (party rotation clipping)

    party_{} -
    {}_truncat
    """
    if n_clicks is None:
        raise PreventUpdate

    # TODO: get etro URL
    set_progress((0, len(job), "Getting LB damage", "Analysis progress:"))
    report_id, fight_id, _ = parse_fflogs_url(fflogs_url)
    encounter_df = read_encounter_table()
    fight_phase = 0
    matched_encounter = encounter_df[
        (encounter_df["report_id"] == report_id)
        & (encounter_df["fight_id"] == fight_id)
    ]
    pet_ids = matched_encounter.set_index("player_id")["pet_ids"].to_dict()
    encounter_id = matched_encounter["encounter_id"].iloc[0]
    level = encounter_level[encounter_id]
    level_step_map = {
        90: {
            "rotation_dmg_step": 20,
            "action_delta": 2,
            "rotation_delta": 10,
        },
        100: {
            "rotation_dmg_step": 20,
            "action_delta": 5,
            "rotation_delta": 15,
        },
    }
    # Get Limit Break instances
    # Check if LB was used, get its ID if it was
    if len(matched_encounter[matched_encounter["job"] == "LimitBreak"]) > 0:
        lb_id = int(
            matched_encounter[matched_encounter["job"] == "LimitBreak"][
                "player_id"
            ].iloc[0]
        )
        lb_damage_events_df = limit_break_damage_events(report_id, fight_id, lb_id)
        lb_damage = lb_damage_events_df["amount"].sum()
    else:
        lb_damage_events_df = pd.DataFrame(columns=["timestamp"])
        lb_damage = 0

    # # Our queen can heal herself, which affects her max HP. Gotta get that
    # if encounter_id in (94,):
    #     boss_healing = boss_healing_amount(report_id, fight_id)
    # else:
    #     boss_healing = 0

    # boss_total_hp = boss_hp[encounter_id] + boss_healing
    # Party bonus to main stat
    main_stat_multiplier = 1 + len(set(main_stat_label)) / 100

    t_clips = [2.5, 5, 7.5, 10]
    # Damage step size for
    rotation_dmg_step = level_step_map[level]["rotation_dmg_step"]
    action_delta = level_step_map[level]["action_delta"]
    rotation_delta = level_step_map[level]["rotation_delta"]
    n_data_points = 5000

    ######
    # Job-level analyses
    ######

    # Whole job rotations
    job_rotation_analyses_list = []
    job_rotation_pdf_list = []
    job_db_rows = []

    # Job rotation clippings to unconvolve out later
    job_rotation_clipping_pdf_list = {t: [] for t in t_clips}
    job_rotation_clipping_analyses = {t: [] for t in t_clips}

    job_analysis_ids = [
        check_prior_job_analyses(
            report_id,
            fight_id,
            player_id[a],
            player_name[a],
            main_stat_no_buff[a],
            secondary_stat_no_buff[a],
            determination[a],
            speed[a],
            crit[a],
            dh[a],
            weapon_damage[a],
            weapon_delays[job[a].upper()],
            medication_amt,
        )
        for a in range(len(job))
    ]

    party_analysis_id, redo_party_analysis = check_prior_party_analysis(
        job_analysis_ids, report_id, fight_id, len(job)
    )
    if redo_party_analysis == 0:
        return f"/party_analysis/{party_analysis_id}"

    # Compute job-level analyses
    for a in range(len(job)):
        full_job = reverse_abbreviated_role_map[job[a]]
        role = role_mapping[full_job]
        delay = weapon_delays[job[a].upper()]

        # Progress bar
        current_job = job_progress(job, job[a])
        set_progress((a, len(job), current_job))

        main_stat_buff = int(main_stat_no_buff[a] * main_stat_multiplier)
        secondary_stat_buff = (
            int(caster_healer_strength[job[a].upper()] * main_stat_multiplier)
            if role in ("Healer", "Magical Ranged")
            else secondary_stat_no_buff[a]
        )
        gearset_id = etro_url[a]

        job_rotation_analyses_list.append(
            RotationTable(
                headers,
                report_id,
                fight_id,
                full_job,
                player_id[a],
                crit[a],
                dh[a],
                determination[a],
                medication_amt,
                level,
                fight_phase,
                damage_buff_table,
                critical_hit_rate_table,
                direct_hit_rate_table,
                guaranteed_hits_by_action_table,
                guaranteed_hits_by_buff_table,
                potency_table,
                pet_ids[player_id[a]],
            )
        )

        job_rotation_pdf_list.append(
            rotation_analysis(
                role,
                full_job,
                job_rotation_analyses_list[a].rotation_df,
                1,
                main_stat_buff,
                secondary_stat_buff,
                determination[a],
                speed[a],
                crit[a],
                dh[a],
                weapon_damage[a],
                delay,
                main_stat_no_buff[a],
                rotation_step=rotation_dmg_step,
                rotation_delta=rotation_delta,
                action_delta=action_delta,
                compute_mgf=False,
                level=level,
            )
        )

        # Assign analysis ID
        # only append if analysis ID is None so the ID isn't overwritten
        if job_analysis_ids[a] is None:
            job_analysis_ids[a] = str(uuid4())
        main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"]
        secondary_stat_type = role_stat_dict[role]["secondary_stat"]["placeholder"]
        gearset_id, _ = parse_etro_url(gearset_id)

        # Collect DB rows to insert at the end
        job_db_rows.append(
            (
                job_analysis_ids[a],
                report_id,
                fight_id,
                fight_phase,
                encounter_name,
                job_rotation_analyses_list[a].fight_time,
                full_job,
                player_name[a],
                int(main_stat_no_buff[a]),
                int(main_stat_buff),
                main_stat_type,
                secondary_stat_no_buff[a],
                secondary_stat_buff,
                secondary_stat_type,
                int(determination[a]),
                int(speed[a]),
                int(crit[a]),
                int(dh[a]),
                int(weapon_damage[a]),
                delay,
                medication_amt,
                main_stat_multiplier,
                gearset_id,
                0,
                0,
            )
        )

        actions_df = job_rotation_analyses_list[a].actions_df
        if role in ("Healer", "Magical Ranged"):
            actions_df = actions_df[actions_df["ability_name"] != "attack"]

        # We have to get a little cute here because it's possible for to return an empty rotation
        # If that's the case, we just want to skip over it and not append it, so individual lists
        # of each dataclass are created and appended to if a rotation is returned.
        t_out = []
        clipped_rotations = []
        for idx, t in enumerate(t_clips):
            print(t)
            clipped_rotations.append(
                job_rotation_analyses_list[a].make_rotation_df(
                    actions_df, t_end_clip=t, return_clipped=True
                )
            )
            if clipped_rotations[idx] is not None:
                # Compute mean via MGFs because it is cheap to compute
                # and will be exact. We need the mean later when we unconvolve
                # to create a truncated rotation.
                job_rotation_clipping_analyses[t].append(
                    rotation_analysis(
                        role,
                        full_job,
                        clipped_rotations[idx],
                        1,
                        main_stat_buff,
                        secondary_stat_buff,
                        determination[a],
                        speed[a],
                        crit[a],
                        dh[a],
                        weapon_damage[a],
                        delay,
                        main_stat_no_buff[a],
                        rotation_step=rotation_dmg_step,
                        rotation_delta=rotation_delta,
                        action_delta=action_delta,
                        compute_mgf=True,
                    )
                )
                job_rotation_clipping_pdf_list[t].append(
                    job_rotation_clipping_analyses[t][-1]
                )
                t_out.append(t)

    ########################
    # Party-level analysis
    ########################
    rotation_pdf, rotation_supp = rotation_dps_pdf(job_rotation_pdf_list, lb_damage)

    party_distribution_clipping = {t: {} for t in t_clips}
    truncated_party_distribution = {t: {} for t in t_clips}

    # Create truncated damage distributions for kill time analysis
    rotation_mean = sum([j.rotation_mean for j in job_rotation_pdf_list])
    fight_end_timestamp = job_rotation_analyses_list[0].fight_end_time
    for t in t_clips:
        # Convolve rotation clippings together
        (
            party_distribution_clipping[t]["pdf"],
            party_distribution_clipping[t]["support"],
        ) = rotation_dps_pdf(job_rotation_clipping_pdf_list[t])

        # Subtract out the party rotation clipping
        # More efficient than recomputing the entire rotation,
        # which only very slightly changes.

        # FIXME: Check if any LB damage is lost when a rotation is truncated.
        party_rotation_clipping_mean = sum(
            [j.rotation_mean for j in job_rotation_clipping_analyses[t]]
        )

        # Filter LB damage events that happen within truncated rotation
        lb_damage = lb_damage_events_df[
            lb_damage_events_df["timestamp"] <= (fight_end_timestamp - 1000 * t)
        ]

        # Set to 0 if none exist, otherwise sum amounts.
        if len(lb_damage) == 0:
            lb_damage = 0
        else:
            lb_damage = lb_damage["amount"].sum()

        (
            truncated_party_distribution[t]["pdf"],
            truncated_party_distribution[t]["support"],
        ) = unconvovle_clipped_pdf(
            rotation_pdf,
            party_distribution_clipping[t]["pdf"],
            rotation_supp,
            party_distribution_clipping[t]["support"],
            party_rotation_clipping_mean,
            rotation_mean,
            limit_break_damage=lb_damage,
            dmg_step=rotation_dmg_step,
        )

    ##########################################
    # Export all the data we've generated
    ##########################################

    #
    boss_total_hp = (
        sum([a.actions_df["amount"].sum() for a in job_rotation_analyses_list])
        + lb_damage
    )
    # Job analyses
    for a in range(len(job_rotation_pdf_list)):
        # Write RotationTable
        with open(BLOB_URI / f"rotation-object-{job_analysis_ids[a]}.pkl", "wb") as f:
            pickle.dump(job_rotation_analyses_list[a], f)

        # Convert job analysis to data class
        job_analysis_data = job_analysis_to_data_class(
            job_rotation_pdf_list[a], job_rotation_analyses_list[a].fight_time
        )

        job_analysis_data.interpolate_distributions(
            rotation_n=n_data_points, action_n=n_data_points
        )

        # Write data class
        with open(BLOB_URI / f"job-analysis-data-{job_analysis_ids[a]}.pkl", "wb") as f:
            pickle.dump(job_analysis_data, f)

        # Update report table
        unflag_redo_rotation(job_analysis_ids[a])
        unflag_report_recompute(job_analysis_ids[a])
        update_report_table(job_db_rows[a])
        pass

    # Party analysis
    # Create an ID if it's not a recompute
    if party_analysis_id is None:
        party_analysis_id = str(uuid4())

    party_mean = sum([a.rotation_mean for a in job_rotation_pdf_list])
    party_std = sum([a.rotation_variance for a in job_rotation_pdf_list]) ** (0.5)
    party_skewness = sum(
        [
            a.rotation_skewness * a.rotation_variance ** (3 / 2)
            for a in job_rotation_pdf_list
        ]
    ) / sum([a.rotation_variance ** (3 / 2) for a in job_rotation_pdf_list])

    party_rotation = PartyRotation(
        party_analysis_id,
        boss_total_hp,
        job_rotation_analyses_list[0].fight_time,
        lb_damage_events_df,
        party_mean,
        party_std,
        party_skewness,
        rotation_pdf,
        rotation_supp,
        [
            SplitPartyRotation(
                t,
                boss_total_hp,
                truncated_party_distribution[t]["pdf"],
                truncated_party_distribution[t]["support"],
                party_distribution_clipping[t]["pdf"],
                party_distribution_clipping[t]["support"],
            )
            for t in t_clips
        ],
    )

    party_rotation.interpolate_distributions(
        rotation_n=n_data_points, split_n=n_data_points
    )

    # Write party analysis to disk
    with open(
        BLOB_URI / "party-analyses" / f"party-analysis-{party_analysis_id}.pkl", "wb"
    ) as f:
        pickle.dump(party_rotation, f)

    # Update party report table
    individual_analysis_ids = [None] * 8
    individual_analysis_ids[0 : len(job_analysis_ids)] = job_analysis_ids
    db_row = tuple(
        [
            party_analysis_id,
            report_id,
            fight_id,
            fight_phase,
        ]
        + individual_analysis_ids
        + [0]
    )
    if redo_party_analysis == 1:
        update_party_report_table(db_row)
    else:
        unflag_party_report_recompute(party_analysis_id)

    current_job = "Analysis progress: Done!"
    set_progress((a + 1, len(job), current_job, "Analysis progress:"))
    updated_url = f"/party_analysis/{party_analysis_id}"
    return updated_url
