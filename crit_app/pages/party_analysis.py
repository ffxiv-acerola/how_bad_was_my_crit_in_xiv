import pickle
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import dash
import pandas as pd
from dash import (
    ALL,
    MATCH,
    Input,
    Output,
    State,
    callback,
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
from crit_app.util.dash_elements import error_alert

# from app import app
from crit_app.config import BLOB_URI, DRY_RUN
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
from crit_app.job_data.roles import (
    abbreviated_job_map,
    role_mapping,
    role_stat_dict,
    unabbreviated_job_map,
)
from crit_app.party_cards import (
    create_fflogs_card,
    create_party_accordion_children,
    create_quick_build_table_data,
    create_results_card,
)
from crit_app.shared_elements import (
    etro_build,
    format_kill_time_str,
    get_phase_selector_options,
    rotation_analysis,
    validate_meldable_stat,
    validate_secondary_stat,
    validate_speed_stat,
    validate_weapon_damage,
)
from crit_app.util.db import (
    check_prior_party_analysis,
    get_party_analysis_encounter_info,
    get_party_analysis_player_constituents,
    get_party_analysis_player_info,
    insert_error_party_analysis,
    insert_error_player_analysis,
    search_prior_player_analyses,
    # unflag_party_report_recompute,
    unflag_redo_rotation,
    unflag_report_recompute,
    update_encounter_table,
    update_party_report_table,
    update_report_table,
)
from crit_app.util.party_dps_distribution import (
    PartyRotation,
    SplitPartyRotation,
    kill_time_analysis,
    rotation_dps_pdf,
)
from crit_app.util.player_dps_distribution import job_analysis_to_data_class
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

LEVEL_STEP_MAP = {
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


def layout(party_analysis_id=None):
    if party_analysis_id is None:
        fflogs_card = create_fflogs_card()
        return dash.html.Div([fflogs_card, html.Br(), create_results_card()])

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
        (
            report_id,
            fight_id,
            phase_id,
            last_phase_index,
            encounter_id,
            encounter_name,
            kill_time,
        ) = get_party_analysis_encounter_info(party_analysis_id)

        etro_job_build_information, player_analysis_selector, medication_amount = (
            get_party_analysis_player_constituents(party_analysis_id)
        )
        ############################
        ### FFLogs Card Elements ###
        ############################

        kill_time_str = format_kill_time_str(kill_time)

        phase_selector_options, phase_select_hidden = get_phase_selector_options(
            last_phase_index, encounter_id
        )

        quick_build_data = create_quick_build_table_data(etro_job_build_information)

        party_accordion_children = create_party_accordion_children(
            etro_job_build_information, True
        )

        # FIXME: add to party_card as option
        # collapse_button = dbc.Button(
        #     children="Show party build",
        #     n_clicks=0,
        #     id="party-collapse-button",
        #     class_name="mb-3",
        # )

        fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"
        fflogs_card = create_fflogs_card(
            fflogs_url,
            encounter_name,
            kill_time_str,
            str(phase_id),
            phase_selector_options,
            phase_select_hidden,
            medication_amount,
            quick_build_data,
            party_accordion_children,
            False,
        )

        #############################
        ### Results Card elements ###
        #############################

        analysis_url = (
            f"https://howbadwasmycritinxiv.com/party_analysis/{party_analysis_id}"
        )

        party_dps_figure = make_party_rotation_pdf_figure(party_analysis_obj)
        kill_time_figure = make_kill_time_graph(party_analysis_obj, kill_time)
        player_analysis_selector_options = [
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
            for x in player_analysis_selector
        ]

        results_card = create_results_card(
            analysis_url,
            party_dps_figure,
            kill_time_figure,
            player_analysis_selector_options,
            player_analysis_selector[0][2],
        )

        return html.Div([fflogs_card, html.Br(), results_card])


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
    Output("party-encounter-name", "children"),
    Output("party-kill-time", "children"),
    Output("party-phase-select", "options"),
    Output("party-phase-select-div", "hidden"),
    Output("quick-build-table", "data"),
    Output("party-accordion", "children"),
    Output("party-fflogs-hidden-div", "hidden"),
    Input("fflogs-url-state2", "n_clicks"),
    State("fflogs-url2", "value"),
    prevent_initial_call=True,
)
def party_fflogs_process(n_clicks, url):
    if url is None:
        raise PreventUpdate

    invalid_return = [False, True, [], [], [], True, [], [], True]

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

    # Phase selection
    phase_selector_options, phase_select_hidden = get_phase_selector_options(
        furthest_index_phase, encounter_id
    )

    # Sort by job, player name so the order will always be the same
    job_information = sorted(
        job_information, key=lambda d: (d["job"], d["player_name"], d["player_id"])
    )

    quick_build_table = create_quick_build_table_data(job_information)
    party_accordion_children = create_party_accordion_children(job_information)

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
        encounter_name,
        kill_time_str,
        phase_selector_options,
        phase_select_hidden,
        quick_build_table,
        party_accordion_children,
        False,
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
                # if build_role in ("Healer", "Magical Ranged"):
                #     secondary_stat = int(secondary_stat / etro_party_bonus)

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
    Output("party-analysis-error", "children"),
    Input("party-compute", "n_clicks"),
    State("party-phase-select", "value"),
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
    State("party-encounter-name", "children"),
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
    fight_phase,
    job,
    player_id,
    main_stat_no_buff,
    secondary_stat_no_buff,
    determination,
    speed,
    crit,
    dh,
    weapon_damage,
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
    updated_url = dash.no_update
    if n_clicks is None:
        raise PreventUpdate

    if isinstance(fight_phase, list):
        fight_phase = fight_phase[0]
    else:
        fight_phase = int(fight_phase)

    # TODO: get etro URL
    set_progress((0, len(job), "Getting LB damage", "Analysis progress:"))
    report_id, fight_id, _ = parse_fflogs_url(fflogs_url)
    encounter_id, lb_player_id, pet_id_map = get_party_analysis_player_info(
        report_id, fight_id
    )
    level = encounter_level[encounter_id]

    # Get Limit Break instances
    # Check if LB was used, get its ID if it was
    if lb_player_id is not None:
        lb_damage_events_df = limit_break_damage_events(
            report_id, fight_id, lb_player_id, fight_phase
        )
        lb_damage = lb_damage_events_df["amount"].sum()
    else:
        lb_damage_events_df = pd.DataFrame(columns=["timestamp"])
        lb_damage = 0

    # Party bonus to main stat
    main_stat_multiplier = 1 + len(set(main_stat_label)) / 100

    # FIXME: this needs to be found for fights like FRU
    # Fixed time between phases, need to find killing damage event
    t_clips = [2.5, 5, 7.5, 10]
    # Damage step size for
    rotation_dmg_step = LEVEL_STEP_MAP[level]["rotation_dmg_step"]
    action_delta = LEVEL_STEP_MAP[level]["action_delta"]
    rotation_delta = LEVEL_STEP_MAP[level]["rotation_delta"]
    n_data_points = 5000

    ######
    # Player-level analyses
    ######

    prior_analysis_info = [
        search_prior_player_analyses(
            report_id,
            fight_id,
            fight_phase,
            unabbreviated_job_map[job[a]],
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
    player_analysis_ids = [p[0] for p in prior_analysis_info]
    any_redo_flags = any([p[1] for p in prior_analysis_info])

    if len(set(player_analysis_ids)) == 8:
        party_analysis_id = check_prior_party_analysis(player_analysis_ids)
    else:
        party_analysis_id = None

    if (party_analysis_id is not None) and (not any_redo_flags):
        return f"/party_analysis/{party_analysis_id}", []

    # Compute player-level analyses
    success, results = player_analysis_loop(
        report_id,
        fight_id,
        encounter_name,
        encounter_id,
        player_name,
        player_id,
        fight_phase,
        pet_id_map,
        job,
        set_progress,
        main_stat_no_buff,
        main_stat_multiplier,
        secondary_stat_no_buff,
        speed,
        determination,
        crit,
        dh,
        weapon_damage,
        medication_amt,
        level,
        etro_url,
        player_analysis_ids,
        t_clips,
    )

    if success:
        (
            job_rotation_analyses_list,
            job_rotation_pdf_list,
            job_db_rows,
            job_rotation_clipping_pdf_list,
            job_rotation_clipping_analyses,
        ) = results

    else:
        error_message = results[-2]
        insert_error_player_analysis(*results)
        return updated_url, [error_alert(error_message)]
    ########################
    # Party-level analysis
    ########################
    try:
        rotation_pdf, rotation_supp = rotation_dps_pdf(job_rotation_pdf_list, lb_damage)

        truncated_party_distribution, party_distribution_clipping = kill_time_analysis(
            job_rotation_analyses_list,
            job_rotation_pdf_list,
            lb_damage_events_df,
            job_rotation_clipping_analyses,
            job_rotation_clipping_pdf_list,
            rotation_pdf,
            rotation_supp,
            t_clips,
            rotation_dmg_step,
        )

        #
        boss_total_hp = (
            sum([a.actions_df["amount"].sum() for a in job_rotation_analyses_list])
            + lb_damage
        )
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

    except Exception as e:
        party_error_info = (
            report_id,
            fight_id,
            fight_phase,
            encounter_id,
            job,
            player_name,
            player_id,
            main_stat_no_buff,
            secondary_stat_no_buff,
            determination,
            speed,
            crit,
            dh,
            weapon_damage,
            main_stat_multiplier,
            medication_amt,
            etro_url,
            str(e),
            traceback.format_exc(),
        )
        insert_error_party_analysis(*party_error_info)

        return updated_url, [error_alert(str(e))]
    ##########################################
    # Export all the data we've generated
    ##########################################

    # Job analyses
    for a in range(len(job_rotation_pdf_list)):
        # Write RotationTable
        with open(
            BLOB_URI / f"rotation-object-{player_analysis_ids[a]}.pkl", "wb"
        ) as f:
            pickle.dump(job_rotation_analyses_list[a], f)

        # Convert job analysis to data class
        job_analysis_data = job_analysis_to_data_class(
            job_rotation_pdf_list[a], job_rotation_analyses_list[a].fight_time
        )

        job_analysis_data.interpolate_distributions(
            rotation_n=n_data_points, action_n=n_data_points
        )

        # Write data class
        with open(
            BLOB_URI / f"job-analysis-data-{player_analysis_ids[a]}.pkl", "wb"
        ) as f:
            pickle.dump(job_analysis_data, f)

        # Update report table
        unflag_redo_rotation(player_analysis_ids[a])
        unflag_report_recompute(player_analysis_ids[a])
        update_report_table(job_db_rows[a])
        pass

    # Write party analysis to disk
    with open(
        BLOB_URI / "party-analyses" / f"party-analysis-{party_analysis_id}.pkl", "wb"
    ) as f:
        pickle.dump(party_rotation, f)

    # Update party report table
    individual_analysis_ids = [None] * 8
    individual_analysis_ids[0 : len(player_analysis_ids)] = player_analysis_ids
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
    update_party_report_table(db_row)

    current_job = "Analysis progress: Done!"
    set_progress((a + 1, len(job), current_job, "Analysis progress:"))
    updated_url = f"/party_analysis/{party_analysis_id}"
    return updated_url, []


def player_analysis_loop(
    report_id: str,
    fight_id: int,
    encounter_name: str,
    encounter_id: int,
    player_name: List[str],
    player_id: List[int],
    fight_phase: int,
    pet_id_map: Dict[int, Any],
    job: List[str],
    set_progress: Any,
    main_stat_no_buff: List[float],
    main_stat_multiplier: float,
    secondary_stat_no_buff: List[Union[float, str]],
    speed: List[int],
    determination: List[int],
    crit: List[int],
    dh: List[int],
    weapon_damage: List[int],
    medication_amt: int,
    level: int,
    etro_url: List[str],
    player_analysis_ids: List[Optional[str]],
    t_clips: List[float],
) -> Tuple[bool, Union[Tuple[List[Any], List[Any], List[Any], Dict[float, List[Any]], Dict[float, List[Any]]], Tuple[Any, ...]]]:
    """
    Analyzes each player's combat performance by building rotation analyses and PDFs.

    This function:
      1. Retrieves or creates a unique analysis ID for each player.
      2. Builds a rotation analysis DataFrame and PDF for each job in the fight.
      3. Saves the rotation data and associated PDFs into lists and dictionaries
         for future reference.
      4. Catches exceptions to gather and return error information if the analysis fails.

    Args:
        report_id (str): FFLogs report identifier.
        fight_id (int): Numeric identifier for the fight.
        encounter_name (str): Name of the encounter.
        encounter_id (int): Numeric ID of the encounter.
        player_name (List[str]): List of player names.
        player_id (List[int]): List of player IDs.
        fight_phase (int): Current phase in the fight.
        pet_id_map (Dict[int, Any]): Maps player IDs to pet data.
        job (List[str]): List of job abbreviations (e.g. ["DRG", "WHM"]).
        set_progress (Any): Callback to update or display progress.
        main_stat_no_buff (List[float]): Main stat values before buffs for each player.
        main_stat_multiplier (float): Multiplier applied to main stat.
        secondary_stat_no_buff (List[Union[float, str]]): Secondary stat values before buffs.
        speed (List[int]): Speed values for each player's job.
        determination (List[int]): Determination values for each player's job.
        crit (List[int]): Critical hit rate values for each player's job.
        dh (List[int]): Direct hit rate values for each player's job.
        weapon_damage (List[int]): Weapon damage values for each player's job.
        medication_amt (int): Amount of medicine/food buffs applied.
        level (int): Character level used in calculations.
        etro_url (List[str]): Gearset URLs for each player.
        player_analysis_ids (List[Optional[str]]): List of existing or None player analysis IDs.
        t_clips (List[float]): List of time clipping points for truncated analyses.

    Returns:
        Tuple[bool, Union[
            Tuple[
                List[Any],  # job_rotation_analyses_list
                List[Any],  # job_rotation_pdf_list
                List[Any],  # job_db_rows
                Dict[float, List[Any]],  # job_rotation_clipping_pdf_list
                Dict[float, List[Any]]   # job_rotation_clipping_analyses
            ],
            Tuple[Any, ...]  # player_error_info if an exception occurs
        ]]:
        A two-element tuple indicating success (True/False) and either:
         - On success (True), a tuple of lists/dicts containing rotation analyses and PDFs.
         - On failure (False), a tuple of error information.
    """
    rotation_dmg_step = LEVEL_STEP_MAP[level]["rotation_dmg_step"]
    action_delta = LEVEL_STEP_MAP[level]["action_delta"]
    rotation_delta = LEVEL_STEP_MAP[level]["rotation_delta"]

    # Whole job rotations
    job_rotation_analyses_list = []
    job_rotation_pdf_list = []
    job_db_rows = []

    # Job rotation clippings to unconvolve out later
    job_rotation_clipping_pdf_list = {t: [] for t in t_clips}
    job_rotation_clipping_analyses = {t: [] for t in t_clips}

    try:
        a = 0
        for a in range(len(job)):
            full_job = reverse_abbreviated_role_map[job[a]]
            role = role_mapping[full_job]
            delay = weapon_delays[job[a].upper()]

            # Progress bar
            current_job = job_progress(job, job[a])
            set_progress((a, len(job), current_job))

            main_stat_buff = int(main_stat_no_buff[a] * main_stat_multiplier)
            # Assign analysis ID
            # only append if analysis ID is None so the ID isn't overwritten
            if player_analysis_ids[a] is None:
                player_analysis_ids[a] = str(uuid4())
            main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"]

            secondary_stat_type = role_stat_dict[role]["secondary_stat"]["placeholder"]
            secondary_stat_buff = (
                int(caster_healer_strength[job[a].upper()] * main_stat_multiplier)
                if role in ("Healer", "Magical Ranged")
                else secondary_stat_no_buff[a]
            )
            secondary_stat_buff = (
                None if secondary_stat_buff == "None" else secondary_stat_buff
            )

            gearset_id = etro_url[a]
            gearset_id, _ = parse_etro_url(gearset_id)

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
                    pet_id_map[player_id[a]],
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

            # Collect DB rows to insert at the end
            job_db_rows.append(
                (
                    player_analysis_ids[a],
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
                    None
                    if secondary_stat_no_buff[a] == "None"
                    else secondary_stat_no_buff[a],
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
        success = True
        return (
            success,
            (
                job_rotation_analyses_list,
                job_rotation_pdf_list,
                job_db_rows,
                job_rotation_clipping_pdf_list,
                job_rotation_clipping_analyses,
            ),
        )

    except Exception as e:
        success = False
        player_error_info = (
            report_id,
            fight_id,
            player_id[a],
            encounter_id,
            encounter_name,
            fight_phase,
            full_job,
            player_name[a],
            int(main_stat_no_buff[a]),
            int(main_stat_buff),
            main_stat_type,
            None if secondary_stat_no_buff[a] == "None" else secondary_stat_no_buff[a],
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
            str(e),
            traceback.format_exc(),
        )
        return success, (player_error_info)
