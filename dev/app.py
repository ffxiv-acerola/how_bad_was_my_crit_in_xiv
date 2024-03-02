import dash
from dash import dcc, html, Input, Output, State, callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

import coreapi

from api_queries import parse_etro_url, get_encounter_job_info, parse_fflogs_url

from config import DEBUG, ETRO_TOKEN


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    # external_stylesheets=[dbc.themes.BOOTSTRAP],
    # suppress_callback_exceptions=True, # needed because some callbacks use dynamically generated id's
)

app.title = "How bad was my crit in FFXIV?"
server = app.server

header = html.Div(
    [
        dcc.Store(id="store"),
        html.H1("How bad was my crit in FFXIV?"),
        html.P(
            "Have you ever wondered how (un)lucky your critical/direct hit rate and corresponding DPS for a run was? Maybe you crit every action and want to know how likely a better run is and by how much DPS. Or maybe your crit was so bad you would like mathematical proof quantifying just how unlucky you are."
        ),
        html.P(
            "For a given run, howbadwasmycritinxiv pulls your rotation and how much damage each action did from FFLogs. Using your job build, it exactly simulates how likely all possible DPS values are due to damage variability and compares it to your actual DPS. To get started, all you need is your job build and link to a fight log."
        ),
        html.Hr(),
    ]
)

etro_url = None
main_stat = (None,)
secondary_stat = None
determination = None
speed = None
crit = None
direct_hit = None
weapon_damage = None
delay = None
party_bonus = 1.05
medication_amt = 262


role_input = dbc.Row(
    [
        dbc.Label("Role", width=12, md=2),
        dbc.Col(
            [dbc.Select(["Healer", "Tank"], "Healer", id="role-select")], width=12, md=5
        ),
    ],
    class_name="mb-3",
)


job_build_card = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                html.H2("Select a role and enter job build"),
                html.P(
                    "A job build must be fully entered before a log can be analyzed. A build from an Etro URL can be loaded in or values can be manually entered. A role must be selected so the correct main/secondary stats can be used. If an Etro build is used, the role will be automatically selected."
                ),
                dbc.Form(
                    [

                        role_input,

                    ]
                ),
            ]
        )
    )
)




fflogs_url = None
encounter_info = []
job_radio_options = []
job_radio_value = None
analyze_hidden = False

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
        html.H3("Select a job", id="select-job"),
        dbc.Label("Tanks:"),
        dbc.RadioItems(
            value=job_radio_value,
            options=job_radio_options,
            id="tank-jobs",
        ),
        dbc.Label("Healers:"),
        dbc.RadioItems(
            value=job_radio_value,
            options=job_radio_options,
            id="healer-jobs",
        ),
        dbc.Label("Melee:"),
        dbc.RadioItems(
            value=job_radio_value,
            options=job_radio_options,
            id="melee-jobs",
        ),
        dbc.Label("Physical Ranged:"),
        dbc.RadioItems(
            value=job_radio_value,
            options=job_radio_options,
            id="physical-ranged-jobs",
        ),
        dbc.Label("Magical Ranged:"),
        dbc.RadioItems(
            value=job_radio_value,
            options=job_radio_options,
            id="magical-ranged-jobs",
        ),
    ]
)

fflogs_card = dbc.Card(
    dbc.CardBody(
        [
            html.H2("Enter log to analyze"),
            dbc.Form([fflogs_url, encounter_info]),
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
    id="fflogs-card",
)


fflogs_card = dbc.Card(
    dbc.CardBody(
        [
            html.H2("Enter log to analyze"),
            dbc.Form([fflogs_url, encounter_info]),
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
    id="fflogs-card",
)

app.layout = dbc.Container(
    [header, job_build_card, fflogs_card],
    fluid="md",
)


def show_job_options(job_information, role):
    """
    Show which jobs are available to analyze with radio buttons.
    """
    tank_radio_items = []
    healer_radio_items = []
    melee_radio_items = []
    physical_ranged_radio_items = []
    magical_ranged_radio_items = []

    for d in job_information:
        # Add space to job name
        job_name_space = "".join(
            " " + char if char.isupper() else char.strip() for char in d["job"]
        ).strip()
        label_text = f"{job_name_space} ({d['player_name']})"

        if d["role"] == "Tank":
            tank_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": "Tank" != role,
                }
            )
        elif d["role"] == "Healer":
            healer_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": "Healer" != role,
                }
            )
        elif d["role"] == "Melee":
            melee_radio_items.append(
                {
                    "label": label_text + " [Unsupported]",
                    "value": d["player_id"],
                    "disabled": "Melee" != role,
                }
            )
        elif d["role"] == "Physical Ranged":
            physical_ranged_radio_items.append(
                {
                    "label": label_text + " [Unsupported]",
                    "value": d["player_id"],
                    "disabled": "Physical Ranged" != role,
                }
            )
        elif d["role"] == "Magical Ranged":
            magical_ranged_radio_items.append(
                {
                    "label": label_text + " [Unsupported]",
                    "value": d["player_id"],
                    "disabled": "Magical Ranged" != role,
                }
            )

    return (
        tank_radio_items,
        healer_radio_items,
        melee_radio_items,
        physical_ranged_radio_items,
        magical_ranged_radio_items,
    )


@callback(
    Output("fflogs-url-feedback", "children"),
    Output("read-fflogs-url", "children"),
    Output("select-job", "children"),
    Output("tank-jobs", "options"),
    Output("tank-jobs", "value"),
    Output("healer-jobs", "options"),
    Output("healer-jobs", "value"),
    Output("melee-jobs", "options"),
    Output("melee-jobs", "value"),
    Output("physical-ranged-jobs", "options"),
    Output("physical-ranged-jobs", "value"),
    Output("magical-ranged-jobs", "options"),
    Output("magical-ranged-jobs", "value"),
    Output("fflogs-url", "valid"),
    Output("fflogs-url", "invalid"),
    Input("fflogs-url-state", "n_clicks"),
    State("fflogs-url", "value"),
    # State("valid-jobs", "value"),
    State("role-select", "value"),
    prevent_initial_call=True,
)
def process_fflogs_url(n_clicks, url, role):
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
        start_time,
        r,
    ) = get_encounter_job_info(report_id, int(fight_id))

    print(kill_time)
    fight_time_str = f"{int(kill_time // 60)}:{int(kill_time % 60):02d}"

    if encounter_id not in [88, 89, 90, 91, 92]:
        feedback_text = "Sorry, only fights from Anabeiseos are currently supported."
        return feedback_text, [], [], [], radio_value, False, True

    (
        tank_radio_items,
        healer_radio_items,
        melee_radio_items,
        physical_ranged_radio_items,
        magical_ranged_radio_items,
    ) = show_job_options(job_information, role)

    # Clear the value if one already existed.
    # If the selected value from a prior log is a value in the current log,
    # the value will remain set but appear unselected. It can only appear selected
    # by click off and clicking back on. This is impossible if an AST is in the party.
    # This is fixed by just clearing the value. How dumb.
    print(encounter_id, start_time, job_information)

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

    return (
        [],
        f"{encounter_name} ({fight_time_str})",
        "Please select a job:",
        tank_radio_items,
        radio_value,
        healer_radio_items,
        radio_value,
        melee_radio_items,
        radio_value,
        physical_ranged_radio_items,
        radio_value,
        magical_ranged_radio_items,
        radio_value,
        True,
        False,
    )

if __name__ == "__main__":
    app.run(debug=True)
