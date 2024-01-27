import sqlite3
import datetime
import pickle
from uuid import uuid4

from ffxiv_stats.jobs import Healer

import dash
from dash import Input, Output, State, dcc, html, callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import coreapi
import pandas as pd

from dmg_distribution import create_action_df, create_rotation_df, get_dmg_percentile
from figures import (
    make_rotation_pdf_figure,
    make_rotation_percentile_table,
    make_action_pdfs_figure,
    make_action_table,
)
from api_queries import (
    parse_etro_url,
    parse_fflogs_url,
    get_encounter_job_info,
    damage_events,
)
from crit_app.config import DB_URI, BLOB_URI, ETRO_TOKEN, DRY_RUN


dash.register_page(
    __name__,
    path_template="/analysis/<analysis_id>",
    path="/",
)


def initialize_job_build(
    etro_url=None,
    mind=None,
    strength=None,
    determination=None,
    spell_speed=None,
    crit=None,
    direct_hit=None,
    weapon_damage=None,
    delay=None,
    party_bonus=1.05,
    medication_amt=262,
):
    """
    Create the job build div, optionally setting initial values for them.
    Initial values are set when an `analysis_id` is present in the URL.
    Callback decorators require an input to trigger them, which isn't possible
    to automatically trigger them just once.
    There doesn't seem to be a way to set/edit values without a callback except when
    the element is created.
    """
    job_build = html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2("Enter job build"),
                    html.P(
                        "A job build must be fully entered before a log can be analyzed. A build from an Etro URL can be loaded in or values can be manually entered."
                    ),
                    html.Div(
                        [
                            dbc.Form(
                                dbc.Row(
                                    [
                                        dbc.Label("Etro build URL", width=2),
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
                                            [
                                                dbc.Button(
                                                    "Submit",
                                                    color="primary",
                                                    id="etro-url-button",
                                                ),
                                            ],
                                            width=1,
                                        ),
                                    ],
                                    className="g-2",
                                    style={"padding-bottom": "15px"},
                                )
                            ),
                            dbc.Row(id="etro-build-name-div"),
                            dbc.Row(
                                [
                                    dbc.Label("MND:", width=1),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                value=mind,
                                                type="number",
                                                placeholder="Mind",
                                                id="MND",
                                                min=100,
                                                max=4000,
                                                step=1,
                                            ),
                                            dbc.FormFeedback(
                                                "Please enter a number.",
                                                type="invalid",
                                                id="MND-feedback",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Label(
                                        [
                                            html.Span(
                                                "STR",
                                                id="str-tooltip",
                                                style={
                                                    "textDecoration": "underline",
                                                    "textDecorationStyle": "dotted",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            dbc.Tooltip(
                                                "Strength, used for auto-attacks",
                                                target="str-tooltip",
                                            ),
                                        ],
                                        width=1,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                value=strength,
                                                type="number",
                                                placeholder="Strength",
                                                id="STR",
                                                # min=100,
                                                # max=4000,
                                                # step=1,
                                            ),
                                            dbc.FormFeedback(
                                                "Please enter non-zero number.",
                                                type="invalid",
                                                id="STR-feedback",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Label("DET:", width=1),
                                    dbc.Col(
                                        dbc.Input(
                                            value=determination,
                                            type="number",
                                            placeholder="Determination",
                                            id="DET",
                                            min=100,
                                            max=4000,
                                            step=1,
                                        ),
                                        width=2,
                                    ),
                                    dbc.Label(
                                        [
                                            html.Span(
                                                "SPS",
                                                id="sps-tooltip",
                                                style={
                                                    "textDecoration": "underline",
                                                    "textDecorationStyle": "dotted",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            dbc.Tooltip(
                                                "Your Spell Speed stat, not your GCD.",
                                                target="sps-tooltip",
                                            ),
                                            dbc.FormFeedback(
                                                "Please enter your Spell Speed, not GCD.",
                                                type="invalid",
                                                id="SPS-feedback",
                                            ),
                                        ],
                                        width=1,
                                    ),
                                    dbc.Col(
                                        dbc.Input(
                                            value=spell_speed,
                                            type="number",
                                            placeholder="Spell Speed",
                                            id="SPS",
                                        ),
                                        width=2,
                                    ),
                                ],
                                justify="evenly",
                                style={"padding-bottom": "15px"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Label("CRT:", width=1),
                                    dbc.Col(
                                        dbc.Input(
                                            value=crit,
                                            type="number",
                                            placeholder="Critical Hit",
                                            id="CRT",
                                            min=100,
                                            max=4000,
                                            step=1,
                                        ),
                                        width=2,
                                    ),
                                    dbc.Label("DH:", width=1),
                                    dbc.Col(
                                        dbc.Input(
                                            value=direct_hit,
                                            type="number",
                                            placeholder="Direct Hit Rate",
                                            id="DH",
                                            min=100,
                                            max=4000,
                                            step=1,
                                        ),
                                        width=2,
                                    ),
                                    dbc.Label("WD:", width=1),
                                    dbc.Col(
                                        dbc.Input(
                                            value=weapon_damage,
                                            type="number",
                                            placeholder="Weapon Damage",
                                            id="WD",
                                            min=50,
                                            max=200,
                                            step=1,
                                        ),
                                        width=2,
                                    ),
                                    dbc.Label(
                                        [
                                            html.Span(
                                                "DEL",
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
                                        width=1,
                                    ),
                                    dbc.Col(
                                        dbc.Input(
                                            value=delay,
                                            type="number",
                                            placeholder="Delay",
                                            id="DEL",
                                        ),
                                        width=2,
                                    ),
                                ],
                                justify="evenly",
                                style={"padding-bottom": "15px"},
                            ),
                            dbc.Row(id="party-bonus-warning"),
                            dbc.Row(
                                [
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
                                                            r"The % bonus added to main stat for each unique job present. For most cases, this should be 5%. If a job like Phys Ranged is missing, this value should be 4%.",
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
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                [
                                                    html.Span(
                                                        "Tincture grade",
                                                        id="tincture-tooltip",
                                                        style={
                                                            "textDecoration": "underline",
                                                            "textDecorationStyle": "dotted",
                                                            "cursor": "pointer",
                                                        },
                                                    ),
                                                    dbc.Tooltip(
                                                        "If no tincture was used, "
                                                        "keep the default value selected.",
                                                        target="tincture-tooltip",
                                                    ),
                                                ],
                                            ),
                                            dbc.Select(
                                                name="Tincture grade",
                                                id="tincture-grade",
                                                options=[
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
                                        ]
                                    ),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        )
    )
    return job_build


def initialize_fflogs_card(
    fflogs_url=None,
    encounter_info=[],
    job_radio_options=[],
    job_radio_value=None,
    analyze_hidden=True,
):
    fflogs_card = html.Div(
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H2("Enter log to Analyze"),
                        dbc.Form(
                            dbc.Row(
                                [
                                    dbc.Label("Log URL", width=1),
                                    dbc.Col(
                                        [
                                            dbc.Input(
                                                value=fflogs_url,
                                                type="text",
                                                placeholder="Enter FFLogs URL",
                                                id="fflogs-url",
                                            ),
                                            dbc.FormFeedback(
                                                type="invalid", id="fflogs-url-feedback"
                                            ),
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
                                        width=1,
                                    ),
                                ],
                                className="g-2",
                                style={"padding-bottom": "15px"},
                            )
                        ),
                        html.H3(children=encounter_info, id="read-fflogs-url"),
                        dbc.Label("Please select a job:", id="select-job"),
                        dbc.RadioItems(
                            value=job_radio_value,
                            options=job_radio_options,
                            id="valid-jobs",
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
                )
            ]
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
                html.P("The DPS distribution is also summarized by its first three moments: mean, standard deviation, and skewness."),
                html.Div(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    children=rotation_figure, id="rotation-pdf-fig-div"
                                ),
                                width=9,
                            ),
                            dbc.Col(
                                html.Div(
                                    children=rotation_percentile_table,
                                    id="rotation-percentile-div",
                                ),
                                width=3,
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


def initialize_action_card(action_figure=None, action_summary_table=None):
    action_dmg_pdf_card = dbc.Card(
        dbc.CardBody(
            [
                html.H2("Action DPS distributions"),
                html.P(
                    "The DPS distribution for each action is shown below. The table below shows the expected, average DPS, your actual DPS, and the corresponding percentile."
                ),
                html.Div(children=action_figure, id="action-pdf-fig-div"),
                html.Div(children=action_summary_table, id="action-summary-table-div"),
            ],
            className="mb-3",
        ),
    )
    return action_dmg_pdf_card


def initialize_results(
    player_name=None, crit_text=None, rotation_card=[], action_card=[], analysis_url=None, results_hidden=True
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
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Label("Copy analysis link"), align="center", width=2
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
                                            id="clipboard", style={"display": "inline-block"}
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


def read_report_table():
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    report_df = pd.read_sql_query("select * from report", con)

    cur.close()
    con.close()
    return report_df


def read_encounter_table():
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    player_df = pd.read_sql_query("select * from encounter", con)

    cur.close()
    con.close()
    return player_df


def update_report_table(db_row):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert into report 
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def update_encounter_table(db_rows):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.executemany(
        """
    insert into encounter 
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        db_rows,
    )
    # Drop any duplicate records
    cur.execute("""
    delete from encounter 
     where rowid not in (
        select min(rowid)
        from encounter
        group by report_id, fight_id, player_id
     )
    """
    )
    con.commit()
    cur.close()
    con.close()
    pass


def update_access_table(db_row):
    """
    Update access table, keeping track of when and how much an analysis ID is accessed.

    Inputs:
    db_row - tuple, of row to insert. Contains (`analysis_id`, `access_datetime`).
    """
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert into access 
    values (?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def layout(analysis_id=None):
    """ 
    Display a previously-analyzed rotation by its analysis ID.

    If no analysis ID exists, display blank everything.
    """
    if analysis_id is None:
        job_build = initialize_job_build()
        fflogs_card = initialize_fflogs_card()
        rotation_card = initialize_rotation_card()
        action_card = initialize_action_card()
        result_card = initialize_results(rotation_card, action_card, True)
        return dash.html.Div(
            [
                job_build,
                html.Br(),
                fflogs_card,
                html.Br(),
                result_card,
            ]
        )
    else:
        analysis_url = f"https://howbadwasmycritinxiv.com/analysis/{analysis_id}"
        # Check if analysis ID exists, 404 if not
        report_df = read_report_table()
        analysis_details = report_df[report_df["analysis_id"] == analysis_id]

        # Message to display if something goes wrong.
        error_children = [
                html.H2("404 Not Found"),
                html.P(
                    [
                        "The link entered does not exist. ",
                        html.A("Click here", href="/"),
                        " to return home and analyze a rotation."
                    ]
                )
            ]

        # redirect to 404 if no analysis page exists
        if len(analysis_details) == 0:
            return html.Div(error_children)
        else:
            analysis_details = analysis_details.iloc[0]
            # Load in action_df and rotation object to display results
            try:
                action_df = pd.read_parquet(
                    BLOB_URI / f"action-df-{analysis_id}.parquet"
                )
                with open(BLOB_URI / f"rotation-obj-{analysis_id}.pkl", "rb") as outp:
                    job_object = pickle.load(outp)
            except Exception as e:
                error_children.append(html.P(f"The following error was encountered: {str(e)}"))
                return html.Div(error_children)

            # Set job build values
            if (analysis_details["etro_id"] is not None) and (analysis_details["etro_id"] != ""):
                etro_url = f"https://etro.gg/gearset/{analysis_details['etro_id']}"
            else:
                etro_url = None
            # mind = job_object.mind
            mind_pre_bonus = analysis_details["main_stat_pre_bonus"]
            strength_pre_bonus = analysis_details["secondary_stat_pre_bonus"]
            # strength = job_object.strength
            determination = job_object.det
            spell_speed = job_object.dot_speed_stat
            crit = job_object.crit_stat
            direct_hit = job_object.dh_stat
            weapon_damage = job_object.weapon_damage
            delay = job_object.delay

            party_bonus = analysis_details["party_bonus"]
            medication_amt = analysis_details["medication_amount"]
            # DPS of each action + the entire rotation

            action_dps = (
                action_df[["ability_name", "amount"]].groupby("ability_name").sum()
                / job_object.t
            ).reset_index()
            rotation_dps = action_dps["amount"].sum()
            rotation_percentile = (
                get_dmg_percentile(
                    rotation_dps,
                    job_object.rotation_dps_distribution,
                    job_object.rotation_dps_support,
                )
                / 100
            )
            # fflogs url
            # need to read in report/player info from db for
            # * fflogs url
            # * Fight name / duration
            # * Player selection
            # also need to read in player selection info
            report_id = analysis_details["report_id"]
            fight_id = analysis_details["fight_id"]
            fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"

            encounter_df = read_encounter_table()
            encounter_df = encounter_df[
                (encounter_df["report_id"] == report_id)
                & (encounter_df["fight_id"] == fight_id)
            ].drop_duplicates()

            boss_name = analysis_details["encounter_name"]
            fight_duration = encounter_df.iloc[0]["kill_time"]
            fight_duration = (
                f"{int(fight_duration // 60)}:{int(fight_duration % 60):02d}"
            )
            encounter_info = f"{boss_name} ({fight_duration})"

            # This will technically fail if you have two characters with the same name on the same job
            character = analysis_details["player_name"]
            player_id = encounter_df[encounter_df["player_name"] == character].iloc[0]["player_id"]
            job_radio_value = player_id

            # add space to job name
            encounter_df["job"] = (
                encounter_df["job"]
                .str.replace(r"(\w)([A-Z])", r"\1 \2", regex=True)
                .str.strip()
            )
            job_radio_options = show_job_options(encounter_df.to_dict("records"))

            ### Percentile and crit text results
            crit_text = rotation_percentile_text_map(rotation_percentile)
            crit_text += f" Your DPS corresponded to the {rotation_percentile:0.1%} percentile of the DPS distribution. Scroll down to see a detailed analysis of your rotation. Please note that DPS is reported and not rDPS (or any of the derived DPS metrics) and that this percentile has no relation to percentiles reported on FFLogs."

            ### make rotation card results
            rotation_fig = make_rotation_pdf_figure(job_object, rotation_dps)
            rotation_graph = (
                dcc.Graph(
                    figure=rotation_fig,
                    id="rotation-pdf-fig",
                ),
            )

            rotation_percentile_table = make_rotation_percentile_table(
                job_object, rotation_percentile
            )

            ### make action card results
            action_fig = make_action_pdfs_figure(job_object, action_dps)
            action_graph = [dcc.Graph(figure=action_fig, id="action-pdf-fig")]

            action_summary_table = make_action_table(
                job_object, action_df, job_object.t
            )

            rotation_graph = rotation_graph[0]
            rotation_percentile_table = rotation_percentile_table[0]
            action_graph = action_graph[0]
            action_summary_table = action_summary_table[0]

            # Crit result text
            crit_text = rotation_percentile_text_map(rotation_percentile)
            crit_text += f" Your DPS corresponded to the {rotation_percentile:0.1%} percentile of the DPS distribution. Scroll down to see a detailed analysis of your rotation. Please note that DPS is reported and not rDPS (or any of the derived DPS metrics) and that this percentile has no relation to percentiles reported on FFLogs."

            ### Make all the divs
            job_build = initialize_job_build(
                etro_url,
                mind_pre_bonus,
                strength_pre_bonus,
                determination,
                spell_speed,
                crit,
                direct_hit,
                weapon_damage,
                delay,
                party_bonus,
                medication_amt,
            )
            fflogs_card = initialize_fflogs_card(
                fflogs_url,
                encounter_info,
                job_radio_options,
                job_radio_value,
                False,
            )
            rotation_card = initialize_rotation_card(
                rotation_graph, rotation_percentile_table
            )
            action_card = initialize_action_card(action_graph, action_summary_table)
            result_card = initialize_results(
                character, crit_text, rotation_card, action_card, analysis_url, False
            )

            access_db_row = (analysis_id, datetime.datetime.now())
            # update access table
            if not DRY_RUN:
                update_access_table(access_db_row)

            return dash.html.Div(
                [
                    job_build,
                    html.Br(),
                    fflogs_card,
                    html.Br(),
                    result_card,
                ]
            )


@callback(
    Output("etro-url-feedback", "children"),
    Output("etro-url", "valid"),
    Output("etro-url", "invalid"),
    Output("etro-build-name-div", "children"),
    Output("MND", "value"),
    Output("STR", "value"),
    Output("DET", "value"),
    Output("SPS", "value"),
    Output("CRT", "value"),
    Output("DH", "value"),
    Output("WD", "value"),
    Output("DEL", "value"),
    Output("party-bonus-warning", "children"),
    Output("main-stat-slider", "value"),
    Input("etro-url-button", "n_clicks"),
    State("main-stat-slider", "value"),
    State("etro-url", "value"),
)
def process_etro_url(n_clicks, party_bonus, url):
    """
    Get the report/fight ID from an fflogs URL, then determine the encounter ID, start time, and jobs present.
    """

    if n_clicks is None:
        raise PreventUpdate

    gearset_id, error_code = parse_etro_url(url)

    if error_code == 1:
        feedback = "This isn't an etro.gg link..."
        return (
            feedback,
            False,
            True,
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            party_bonus,
        )

    if error_code == 2:
        feedback = (
            "This doesn't appear to be a valid gearset. Please double check the link."
        )
        return (
            feedback,
            False,
            True,
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            party_bonus,
        )

    etro_auth = coreapi.auth.TokenAuthentication(token=ETRO_TOKEN)

    # Initialize a client & load the schema document
    client = coreapi.Client(auth=etro_auth)
    schema = client.get("https://etro.gg/api/docs/")

    gearset_action = ["gearsets", "read"]
    gearset_params = {
        "id": gearset_id,
    }
    build_result = client.action(schema, gearset_action, params=gearset_params)
    job_abbreviated = build_result["jobAbbrev"]
    build_name = build_result["name"]
    build_children = [html.H4(f"Build name: {build_name} ({job_abbreviated})")]

    if job_abbreviated not in ["WHM", "AST", "SGE", "SCH"]:
        feedback = "Etro build is not for a healer job."
        return (
            feedback,
            False,
            True,
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            party_bonus,
        )

    total_params = {}

    for p in build_result["totalParams"]:
        item = dict(p)
        key = item.pop("name")
        total_params[key] = item

    mind = total_params["MND"]["value"]
    dh = total_params["DH"]["value"]
    ch = total_params["CRT"]["value"]
    determination = total_params["DET"]["value"]
    sps = total_params["SPS"]["value"]
    wd = total_params["Weapon Damage"]["value"]
    etro_party_bonus = build_result["partyBonus"]

    if job_abbreviated == "SCH":
        strength = 350
    if job_abbreviated == "WHM":
        strength = 214
    if job_abbreviated == "SGE":
        strength = 233
    if job_abbreviated == "AST":
        strength = 194

    weapon_id = build_result["weapon"]
    weapon_action = ["equipment", "read"]

    weapon_params = {"id": weapon_id}
    weapon_result = client.action(schema, weapon_action, params=weapon_params)
    delay = weapon_result["delay"] / 1000

    print(mind, dh, ch, determination, sps, wd, delay, etro_party_bonus)

    if etro_party_bonus > 1.0:
        bonus_fmt = etro_party_bonus - 1
        warning_row = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                f"Warning! The linked etro build has already applied a {bonus_fmt:.0%} bonus to its main stats. The built-in slider below for adding % bonus to the main has been set to 0% and should not be altered.",
            ],
            color="warning",
            className="d-flex align-items-center",
        )
        return (
            [],
            True,
            False,
            build_children,
            mind,
            strength,
            determination,
            sps,
            ch,
            dh,
            wd,
            delay,
            warning_row,
            1.0,
        )
    return (
        [],
        True,
        False,
        build_children,
        mind,
        strength,
        determination,
        sps,
        ch,
        dh,
        wd,
        delay,
        [],
        party_bonus,
    )


@callback(
    Output("fflogs-card", "hidden"),
    Input("MND", "value"),
    Input("STR", "value"),
    Input("DET", "value"),
    Input("SPS", "value"),
    Input("CRT", "value"),
    Input("DH", "value"),
    Input("WD", "value"),
    Input("DEL", "value"),
    Input("results-div", "hidden"),
)
def job_build_defined(
    mind,
    strength,
    determination,
    spell_speed,
    crit,
    direct_hit,
    weapon_damage,
    delay,
    results_hidden,
):
    """
    Check if any job build elements are missing, hide everything else if they are.
    """
    job_build_missing = any(
        elem is None
        for elem in [
            mind,
            strength,
            determination,
            spell_speed,
            crit,
            direct_hit,
            weapon_damage,
            delay,
        ]
    )
    return job_build_missing


@callback(Output("STR", "valid"), Output("STR", "invalid"), Input("STR", "value"))
def validate_str(strength):
    if (strength is None) or (strength > 10):
        return True, False
    else:
        return False, True


@callback(Output("SPS", "valid"), Output("SPS", "invalid"), Input("SPS", "value"))
def validate_sps(spell_speed):
    if (spell_speed is None) or (spell_speed > 3):
        return True, False
    else:
        return False, True


@callback(Output("DEL", "valid"), Output("DEL", "invalid"), Input("DEL", "value"))
def validate_del(delay):
    if (delay is None) or (delay, 4):
        return True, False
    else:
        return False, True


def show_job_options(job_information):
    """
    Show which jobs are available to analyze with radio buttons.
    """
    radio_items = []

    for d in job_information:
        # Add space to job name
        job_name_space = "".join(
            " " + char if char.isupper() else char.strip() for char in d["job"]
        ).strip()
        label_text = f"{job_name_space} ({d['player_name']})"
        if job_name_space != "Astrologian":
            radio_items.append({"label": label_text, "value": d["player_id"]})
        else:
            radio_items.append(
                {
                    "label": label_text + " [Job unsupported]",
                    "value": d["player_id"],
                    "disabled": True,
                    "label_id": "invalid-radio",
                }
            )
    return radio_items


@callback(
    Output("fflogs-url-feedback", "children"),
    Output("read-fflogs-url", "children"),
    Output("select-job", "children"),
    Output("valid-jobs", "options"),
    Output("valid-jobs", "value"),
    Output("fflogs-url", "valid"),
    Output("fflogs-url", "invalid"),
    Input("fflogs-url-state", "n_clicks"),
    State("fflogs-url", "value"),
    State("valid-jobs", "value"),
    prevent_initial_call=True,
)
def process_fflogs_url(n_clicks, url, current_job_selection):
    """
    Get the report/fight ID from an fflogs URL, then determine the encounter ID, start time, and jobs present.
    """

    if url is None:
        raise PreventUpdate
    radio_value = None

    report_id, fight_id, error_code = parse_fflogs_url(url)
    if error_code == 1:
        return "This link isn't FFLogs...", [], [], [], radio_value, False, True

    if error_code == 2:
        feedback_text = "Please enter a log linked to a specific kill."
        return feedback_text, [], [], [], radio_value, False, True

    if error_code == 3:
        feedback_text = "Invalid report ID."
        return feedback_text, [], [], [], radio_value, False, True

    (
        encounter_id,
        start_time,
        job_information,
        kill_time,
        encounter_name,
        r,
    ) = get_encounter_job_info(report_id, int(fight_id))

    print(kill_time)
    fight_time_str = f"{int(kill_time // 60)}:{int(kill_time % 60):02d}"

    if encounter_id not in [88, 89, 90, 91, 92]:
        feedback_text = "Sorry, only fights from Anabeiseos are currently supported."
        return feedback_text, [], [], [], radio_value, False, True

    radio_items = show_job_options(job_information)

    # Clear the value if one already existed.
    # If the selected value from a prior log is a value in the current log,
    # the value will remain set but appear unselected. It can only appear selected
    # by click off and clicking back on. This is impossible if an AST is in the party.
    # This is fixed by just clearing the value. How dumb.
    print(encounter_id, start_time, job_information)

    # FIXME: get player ID and server from r
    db_rows = [
        (
            report_id,
            fight_id,
            encounter_id,
            encounter_name,
            kill_time,
            k["player_name"],
            k["player_server"],
            k["player_id"],
            k["job"],
            "healer",
        )
        for k in job_information
    ]
    if not DRY_RUN:
        update_encounter_table(db_rows)

    return (
        [],
        f"{encounter_name} ({fight_time_str})",
        "Please select a job:",
        radio_items,
        radio_value,
        True,
        False,
    )


@callback(
    Output("compute-dmg-div", "hidden"),
    Input("valid-jobs", "options"),
    Input("valid-jobs", "value"),
    State("valid-jobs", "value"),
)
def display_compute_button(job_list, selected_job, c):
    """
    Display button to compute DPS distributions once a job is selected. Otherwise, no button is shown.
    """
    if job_list is None or selected_job is None:
        raise PreventUpdate

    # Get just the job names
    job_list = [x["value"] for x in job_list]
    if selected_job not in job_list:
        hide_button = True
        return hide_button
    else:
        hide_button = False
        return hide_button


def rotation_percentile_text_map(rotation_percentile):
    """
    Fun text to display depending on the percentile.
    """
    if rotation_percentile <= 0.2:
        return "On second thought, let's pretend this run never happened..."
    elif (rotation_percentile > 0.2) and (rotation_percentile <= 0.4):
        return "BADBADNOTGOOD."
    elif (rotation_percentile > 0.4) and (rotation_percentile <= 0.65):
        return "Mid."
    elif (rotation_percentile > 0.65) and (rotation_percentile <= 0.85):
        return "Actually pretty good."
    elif (rotation_percentile > 0.85) and (rotation_percentile <= 0.95):
        return "Really good."
    elif (rotation_percentile > 0.95) and (rotation_percentile <= 0.99):
        return "Incredibly good."
    elif rotation_percentile > 0.99:
        return "Personally blessed by Yoshi-P himself."


@callback(
    Output("compute-dmg-button", "children"),
    Output("compute-dmg-button", "disabled"),
    Input("compute-dmg-button", "n_clicks"),
    prevent_initial_call=True,
)
def disable_analyze_button(n_clicks):
    """
    Return a disabled, spiny button when the log/rotation is being analyzed.
    """
    if n_clicks is None:
        return ["Analyze rotation"], False
    else:
        return [dbc.Spinner(size="sm"), " Analyzing your log..."], True

@callback(
    Output("clipboard", "content"),
    Input("clipboard", "n_clicks"),
    State("analysis-link", "value"),
)
def copy_analysis_link(n, selected):
    """
    Copy analysis link to clipboard
    """
    if selected is None:
        return "No selections"
    return selected

# This is where all the computation happens
@callback(
    Output("url", "href"),
    Output("compute-dmg-button", "children", allow_duplicate=True),
    Output("compute-dmg-button", "disabled", allow_duplicate=True),
    # Output("results-div", "hidden"),
    Output("crit-result-text", "children"),
    # Output("rotation-pdf-fig-div", "children"),
    # Output("rotation-percentile-div", "children"),
    # Output("action-pdf-fig-div", "children"),
    # Output("action-summary-table-div", "children"),
    Input("compute-dmg-button", "n_clicks"),
    State("MND", "value"),
    State("STR", "value"),
    State("DET", "value"),
    State("SPS", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    State("DEL", "value"),
    State("main-stat-slider", "value"),
    State("tincture-grade", "value"),
    State("valid-jobs", "value"),
    State("fflogs-url", "value"),
    State("etro-url", "value"),
    # prevent_initial_call="initial_duplicate",
    prevent_initial_call=True,
)
def analyze_and_register_rotation(
    n_clicks,
    mind_pre_bonus,
    strength_pre_bonus,
    determination,
    sps,
    ch,
    dh,
    wd,
    delay,
    main_stat_multiplier,
    medication_amt,
    job_player,
    fflogs_url,
    etro_url,
):
    updated_url = dash.no_update

    if n_clicks is None:
        raise PreventUpdate
        # return updated_url, ["Analyze rotation"], False, True, [], [], [], [], []
    report_id, fight_id, _ = parse_fflogs_url(fflogs_url)
    encounter_df = read_encounter_table()
    encounter_comparison_columns = [
        "report_id", "fight_id", "player_id"
    ]

    player_info = encounter_df.loc[
                (encounter_df[encounter_comparison_columns] == (report_id, fight_id, job_player)).all(axis=1)
            ].iloc[0]

    player = player_info["player_name"]
    job_no_space = player_info["job"]
    mind = int(mind_pre_bonus * main_stat_multiplier)
    strength = int(strength_pre_bonus * main_stat_multiplier)

    # Actual value for these attributes don't values matter, except tenacity
    intelligence = 100
    vit = 100
    dexterity = 100
    sks = 400
    ten = 400
    medication_amt = int(medication_amt)
    # Predefined values from: https://www.fflogs.com/reports/NJz2cbM4mZd1hajC#fight=12&type=damage-done
    # which is useful for debugging

    # mind = 3533
    # intelligence = 410
    # vit = 3618
    # strength = 213
    # dexterity = 411
    # determination = 2047
    # sks = 400
    # sps = 664
    # ten = 400
    # dh = 1012
    # ch = 2502
    # wd = 132
    # delay = 3.44

    try:
        gearset_id, error_code = parse_etro_url(etro_url)
        if error_code != 0:
            gearset_id = None

        # Check if the rotation has been analyzed before
        
        prior_reports = read_report_table()
        comparison_columns = [
            "report_id",
            "fight_id",
            "job",
            "player_name",
            "main_stat",
            "secondary_stat",
            "determination",
            "speed",
            "critical_hit",
            "direct_hit",
            "weapon_damage",
            "delay",
            "medication_amount",
        ]

        db_check = (
            report_id,
            fight_id,
            job_no_space,
            player,
            mind,
            strength,
            determination,
            sps,
            ch,
            dh,
            wd,
            delay,
            medication_amt,
        )

        if len(prior_reports) > 0:
            prior_analysis = prior_reports.loc[
                (prior_reports[comparison_columns] == db_check).all(axis=1)
            ]
        else:
            prior_analysis = []

        # FIXME: redirect to variable path
        if len(prior_analysis) >= 1:
            # redirect instead
            analysis_id = prior_analysis["analysis_id"].iloc[0]
            updated_url = f"/analysis/{analysis_id}"
            return (
                updated_url,
                ["Analyze rotation"],
                False,
                [],
            )

        # FIXME: only analyze and write results, redirect to display results
        if len(prior_analysis) == 0:
            actions, t, encounter_name = damage_events(
                report_id, fight_id, job_no_space
            )
            action_df = create_action_df(actions, ch, dh, job_no_space, medication_amt)
            rotation_df = create_rotation_df(action_df)

            # TODO: eventually switch around by job type
            main_stat_type = "mind"
            secondary_stat_type = "strength"
            job_obj = Healer(
                mind,
                intelligence,
                vit,
                strength,
                dexterity,
                determination,
                sks,
                sps,
                ten,
                ch,
                dh,
                wd,
                delay,
            )
            job_obj.attach_rotation(rotation_df, t, convolve_all=True, delta=100)
            job_obj.action_moments = [None] * len(job_obj.action_moments)

            analysis_id = str(uuid4())

            if not DRY_RUN:
                action_df.to_parquet(BLOB_URI / f"action-df-{analysis_id}.parquet")
                with open(BLOB_URI / f"rotation-obj-{analysis_id}.pkl", "wb") as outp:
                    pickle.dump(job_obj, outp, pickle.HIGHEST_PROTOCOL)

                db_row = (
                    analysis_id,
                    report_id,
                    fight_id,
                    encounter_name,
                    t,
                    job_no_space,
                    player,
                    mind_pre_bonus,
                    mind,
                    main_stat_type,
                    strength_pre_bonus,
                    strength,
                    secondary_stat_type,
                    determination,
                    sps,
                    ch,
                    dh,
                    wd,
                    delay,
                    medication_amt,
                    main_stat_multiplier,
                    gearset_id,
                )
                update_report_table(db_row)

            del job_obj

    # Catch any error and display it, then reset the button/prompt
    except Exception as e:
        print(e)
        return (
            updated_url["Analyze rotation"],
            False,
            [
                dbc.Alert(
                    [
                        html.P("The following error was encountered:"),
                        str(e),
                    ],
                    color="danger",
                )
            ],
        )
    updated_url = f"/analysis/{analysis_id}"
    return (updated_url, ["Analyze rotation"], False, [])
