import dash
from dash import Input, Output, State, dcc, html, callback, Patch, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from api_queries import (
    parse_etro_url,
    parse_fflogs_url,
    get_encounter_job_info,
    headers,
)
from job_data.roles import role_stat_dict

import json

from config import ETRO_TOKEN
from shared_elements import etro_build

# from pages.analysis import show_job_options, update_encounter_table, get_encounter_job_info
# from config import DRY_RUN

dash.register_page(
    __name__,
    path_template="/party_analysis/<party_analysis_id>",
    path="/party_analysis",
)

fflogs_url = None
encounter_info = None


fflogs_url = dbc.Row(
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
            [
                dbc.Button(
                    "Submit",
                    color="primary",
                    id="fflogs-url-state2",
                ),
            ],
            width="auto",
        ),
    ],
    class_name="mb-3",
    style={"padding-bottom": "15px"},
)

encounter_info = dbc.Row([], id="encounter-info")

fflogs_card = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                html.H2("Enter log to analyze"),
                dbc.Form([fflogs_url, encounter_info]),
            ]
        ),
    ),
    id="fflogs-card",
)


def layout(party_analysis_id=None):
    if party_analysis_id is None:
        return dash.html.Div([fflogs_card])


def create_job_build_content(
    role: str,
    id_idx: int,
    job: str = None,
    main_stat=None,
    secondary_stat=None,
    determination=None,
    speed=None,
    crit=None,
    direct_hit=None,
    weapon_damage=None,
    delay=None,
):
    role_labels = role_stat_dict[role]
    role_id = role.lower().replace(" ", "-")
    top_stat_list = [
        dbc.Label(
            children=role_labels["main_stat"]["label"],
            width=12,
            md=1,
            id={"type": f"main-stat-label-{role_id}", "index": id_idx},
        ),
        dbc.Col(
            dbc.Input(
                value=main_stat,
                type="number",
                placeholder=role_labels["main_stat"]["placeholder"],
                min=100,
                max=4000,
                id={"type": f"main-stat-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            children=role_labels["secondary_stat"]["label"],
            width=12,
            md=1,
            id={"type": f"secondary-stat-label-{role_id}", "index": id_idx},
        ),
        dbc.Col(
            dbc.Input(
                value=secondary_stat,
                type="number",
                placeholder=role_labels["secondary_stat"]["placeholder"],
                min=100,
                max=4000,
                disabled=True if role in ("Melee", "Physical Ranged") else False,
                id={"type": f"secondary-stat-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            children="DET:",
            width=12,
            md=1,
            id={"type": f"det-label-{role_id}", "index": id_idx},
        ),
        dbc.Col(
            dbc.Input(
                value=determination,
                type="number",
                placeholder="Determination",
                min=100,
                max=4000,
                id={"type": f"DET-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            children=[
                html.Span(
                    children=role_labels["speed_stat"]["label"],
                    id=f"speed-tooltip-{role_id}-{id_idx}",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Your Skill/Spell Speed stat, not your GCD.",
                    target=f"speed-tooltip-{role_id}-{id_idx}",
                ),
                dbc.FormFeedback(
                    "Please enter your Skill/Spell Speed stat, not GCD.",
                    type="invalid",
                    id=f"speed-feedback-{role_id}-{id_idx}",
                ),
            ],
            width=12,
            md=1,
            id=f"speed-stat-label-{role_id}-{id_idx}",
        ),
        dbc.Col(
            dbc.Input(
                value=speed,
                type="number",
                placeholder=role_labels["speed_stat"]["placeholder"],
                min=100,
                max=4000,
                id={"type": f"speed-stat-{role_id}", "index": id_idx},
            )
        ),
    ]

    bottom_stat_list = [
        dbc.Label(
            "CRT:", width=12, md=1, id={"type": f"crt-label-{role_id}", "index": id_idx}
        ),
        dbc.Col(
            dbc.Input(
                value=crit,
                type="number",
                placeholder="Critical Hit",
                min=100,
                max=4000,
                id={"type": f"CRT-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            "DH:", width=12, md=1, id={"type": f"dh-label-{role_id}", "index": id_idx}
        ),
        dbc.Col(
            dbc.Input(
                value=direct_hit,
                type="number",
                placeholder="Direct Hit",
                min=100,
                max=4000,
                id={"type": f"DH-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            "WD:", width=12, md=1, id={"type": f"wd-label-{role_id}", "index": id_idx}
        ),
        dbc.Col(
            dbc.Input(
                value=weapon_damage,
                type="number",
                placeholder="Weapon Damage",
                min=100,
                max=4000,
                id={"type": f"WD-{role_id}", "index": id_idx},
            )
        ),
        dbc.Label(
            [
                html.Span(
                    "DEL:",
                    id=f"del-tooltip-{role_id}-{id_idx}",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Delay, under weapon stats, for auto-attacks. "
                    "Should be a value like 3.44.",
                    target=f"del-tooltip-{role_id}-{id_idx}",
                ),
            ],
            width=12,
            md=1,
            id=f"delay-label-{role_id}-{id_idx}",
        ),
        dbc.Col(
            dbc.Input(
                value=delay,
                type="number",
                placeholder="Delay",
                min=1.0,
                max=4.0,
                id={"type": f"DEL-{role_id}", "index": id_idx},
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

    return html.Div(
        dbc.Form(
            [
                html.H4(id={"type": f"build-name-{role_id}", "index": id_idx}),
                top_stat_row,
                bottom_stat_row,
            ]
        )
    )


def create_accordion_items(role: str, name: str, id_idx: int):
    role_id = role.lower().replace(" ", "-")
    return dbc.AccordionItem(
        children=create_job_build_content(role, id_idx),
        title=[
            dbc.Col(
                dbc.Label(name, id={"type": f"name-{role_id}", "index": id_idx}),
                width=2,
            ),
            dbc.Col(
                [
                    dbc.Input(
                        placeholder=f"Enter Etro build for {name}",
                        id={"type": f"etro-input-{role_id}", "index": id_idx},
                    ),
                    dbc.FormFeedback(
                        type="invalid",
                        id={"type": f"etro-feedback-{role_id}", "index": id_idx},
                    ),
                ],
                width=9,
            ),
        ],
        id={"type": f"accordion-{role_id}", "index": id_idx},
    )


@callback(
    Output("fflogs-url-feedback2", "children"),
    Output("encounter-info", "children"),
    Input("fflogs-url-state2", "n_clicks"),
    State("fflogs-url2", "value"),
    prevent_initial_call=True,
)
def party_fflogs_process(n_clicks, url):
    if n_clicks > 1:
        raise PreventUpdate
    # if url is None:
    #     raise PreventUpdate

    # report_id, fight_id, error_code = parse_fflogs_url(url)

    # if error_code == 1:
    #     return "This link isn't FFLogs...", []
    # elif error_code == 2:
    #     return (
    #         """Please enter a log linked to a specific kill.\nfight=last in the URL is also currently unsupported.""",
    #         [],
    #     )
    # elif error_code == 3:
    #     return "Invalid report ID.", []
    # (
    #     encounter_id,
    #     start_time,
    #     job_information,
    #     kill_time,
    #     encounter_name,
    #     start_time,
    #     r,
    # ) = get_encounter_job_info(report_id, int(fight_id))
    with open("test-party-data.json", "r") as f:
        job_information = json.load(f)

    tanks = [j["player_name"] for j in job_information if j["role"] == "Tank"]
    healers = [j["player_name"] for j in job_information if j["role"] == "Healer"]
    melee = [j["player_name"] for j in job_information if j["role"] == "Melee"]
    physical_ranged = [
        j["player_name"] for j in job_information if j["role"] == "Physical Ranged"
    ]
    casters = [
        j["player_name"] for j in job_information if j["role"] == "Magical Ranged"
    ]

    encounter_children = [
        html.H3(children=encounter_info, id="read-fflogs-url2"),
        html.H2("Enter job builds"),
        html.P(
            "Job builds for all players must be entered. Either enter the Etro link or input each job's stats. Do not include any party composition bonuses to the main stat."
        ),
        dbc.ListGroup(
            [
                dbc.ListGroupItem(
                    [
                        html.H4("Tank"),
                        dbc.Accordion(
                            [
                                create_accordion_items("Tank", j, idx)
                                for idx, j in enumerate(tanks)
                            ],
                            start_collapsed=True,
                        ),
                    ],
                ),
                dbc.ListGroupItem(
                    [
                        html.H4("Healer"),
                        dbc.Accordion(
                            [
                                create_accordion_items("Healer", j, idx)
                                for idx, j in enumerate(healers)
                            ],
                            start_collapsed=True,
                        ),
                    ]
                ),
                dbc.ListGroupItem(
                    [
                        html.H4("Melee"),
                        dbc.Accordion(
                            [
                                create_accordion_items("Melee", j, idx)
                                for idx, j in enumerate(melee)
                            ],
                            start_collapsed=True,
                        ),
                    ]
                ),
                dbc.ListGroupItem(
                    [
                        html.H4("Physical Ranged"),
                        dbc.Accordion(
                            [
                                create_accordion_items("Physical Ranged", j, idx)
                                for idx, j in enumerate(physical_ranged)
                            ],
                            start_collapsed=True,
                        ),
                    ]
                ),
                dbc.ListGroupItem(
                    [
                        html.H4("Magical Ranged"),
                        dbc.Accordion(
                            [
                                create_accordion_items("Magical Ranged", j, idx)
                                for idx, j in enumerate(casters)
                            ],
                            start_collapsed=True,
                        ),
                    ]
                ),
            ]
        ),
        dbc.Button("Validate builds", id="etro-validate"),
    ]
    return "looking good", encounter_children


@callback(
    Output({"type": "main-stat-tank", "index": MATCH}, "value"),
    Output({"type": "secondary-stat-tank", "index": MATCH}, "value"),
    Output({"type": "DET-tank", "index": MATCH}, "value"),
    Output({"type": "speed-stat-tank", "index": MATCH}, "value"),
    Output({"type": "CRT-tank", "index": MATCH}, "value"),
    Output({"type": "DH-tank", "index": MATCH}, "value"),
    Output({"type": "WD-tank", "index": MATCH}, "value"),
    Output({"type": "DEL-tank", "index": MATCH}, "value"),
    Output({"type": "build-name-tank", "index": MATCH}, "children"),
    Output({"type": "etro-input-tank", "index": MATCH}, "valid"),
    Output({"type": "etro-input-tank", "index": MATCH}, "invalid"),
    Output({"type": "etro-feedback-tank", "index": MATCH}, "children"),
    Input("etro-validate", "n_clicks"),
    State({"type": "etro-input-tank", "index": MATCH}, "value"),
)


@callback(
    output={

    }
)
def etro_process(n_clicks, url):
    if n_clicks is None:
        raise PreventUpdate
    gearset_id, error_code = parse_etro_url(url)

    feedback = []
    invalid_return = [
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        [],
        False,
        True,
    ]

    if error_code == 0:
        (
            build_name,
            build_role,
            primary_stat,
            secondary_stat,
            determination,
            speed,
            ch,
            dh,
            wd,
            delay,
            etro_party_bonus,
        ) = etro_build(gearset_id)

        # Make sure Tank build is used
        if build_role != "Tank":
            feedback = "A non-tank etro build was used."
            invalid_return.append(feedback)
            return tuple(invalid_return)

        # If a party bonus is applied in etro, undo it.
        if etro_party_bonus > 1:
            primary_stat = int(primary_stat / etro_party_bonus)
            # Undo STR for healer/caster
            if build_role in ("Healer", "Magical Ranged"):
                secondary_stat = int(secondary_stat / etro_party_bonus)
        return (
            primary_stat,
            secondary_stat,
            determination,
            speed,
            ch,
            dh,
            wd,
            delay,
            f"Build name: {build_name}",
            True,
            False,
            [],
        )

    elif error_code == 1:
        feedback = "This isn't an etro.gg link..."
        invalid_return.append(feedback)
        return tuple(invalid_return)
    elif error_code == 2:
        feedback = (
            "This doesn't appear to be a valid gearset. Please double check the link."
        )
        invalid_return.append(feedback)
        return tuple(invalid_return)


def validate_job_builds():
    pass
