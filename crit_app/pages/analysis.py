import datetime
import pickle
import traceback
from typing import Any
from uuid import uuid4

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from crit_app.cards import (
    initialize_action_card,
    initialize_fflogs_card,
    initialize_job_build,
    initialize_new_action_card,
    initialize_results,
    initialize_rotation_card,
)
from crit_app.config import BLOB_URI, DEBUG, DRY_RUN
from crit_app.dmg_distribution import (
    get_dps_dmg_percentile,
)
from crit_app.figures import (
    make_action_box_and_whisker_figure,
    make_action_pdfs_figure,
    make_rotation_pdf_figure,
    make_rotation_percentile_table,
)
from crit_app.job_data.encounter_data import (
    encounter_level,
    encounter_phases,
    stat_ranges,
    valid_encounters,
)
from crit_app.job_data.job_data import weapon_delays
from crit_app.job_data.job_warnings import job_warnings
from crit_app.job_data.roles import abbreviated_job_map, role_stat_dict
from crit_app.player_elements import (
    rotation_percentile_text_map,
    show_job_options,
)
from crit_app.shared_elements import (
    format_kill_time_str,
    get_phase_selector_options,
    rotation_analysis,
    set_secondary_stats,
    validate_meldable_stat,
    validate_weapon_damage,
)
from crit_app.util.api.fflogs import (
    _query_last_fight_id,
    encounter_information,
    headers,
    parse_fflogs_url,
)
from crit_app.util.api.job_build import (
    etro_build,
    job_build_provider,
    parse_build_uuid,
    reconstruct_job_build_url,
    xiv_gear_build,
)
from crit_app.util.dash_elements import error_alert
from crit_app.util.db import (
    check_valid_player_analysis_id,
    compute_party_bonus,
    get_player_analysis_job_records,
    insert_error_player_analysis,
    player_analysis_meta_info,
    read_player_analysis_info,
    retrieve_player_analysis_information,
    search_prior_player_analyses,
    unflag_redo_rotation,
    unflag_report_recompute,
    update_access_table,
    update_encounter_table,
    update_player_analysis_creation_table,
    update_report_table,
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

valid_stat_return = (True, False)
invalid_stat_return = (False, True)


def page_title(analysis_id=None):
    valid_analysis_id = check_valid_player_analysis_id(analysis_id)
    if not valid_analysis_id:
        return ""

    player_name, job, encounter_name, kill_time = player_analysis_meta_info(analysis_id)

    return "Analysis: {} ({}); {} ({})".format(
        player_name,
        abbreviated_job_map[job].upper(),
        encounter_name,
        format_kill_time_str(kill_time),
    )


def metas(analysis_id: str = None) -> list[dict[str, str]]:
    """
    Generate meta tags for the analysis page.

    Parameters:
    analysis_id (str, optional): The ID of the analysis. Defaults to None.

    Returns:
    list[dict[str, str]]: A list of dictionaries containing meta tag properties and content.
    """
    valid_analysis_id = check_valid_player_analysis_id(analysis_id)
    if not valid_analysis_id:
        player_name, job, encounter_name, kill_time = player_analysis_meta_info(
            analysis_id
        )

        app_description = "Analysis: {} ({}); {} ({})".format(
            player_name,
            abbreviated_job_map[job].upper(),
            encounter_name,
            format_kill_time_str(kill_time),
        )
    else:
        app_description = "Analyze crit RNG for FFXIV!"
    app_image = "crit_app/assets/meta_image.png"
    app_image = "https://i.imgur.com/FVqWdiI.png"
    page_title = "Player analysis"

    return [
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"property": "twitter:url", "content": "https://www.howbadwasmycritinxiv.com/"},
        {"property": "twitter:title", "content": page_title},
        {"property": "twitter:description", "content": app_description},
        {"property": "twitter:image", "content": app_image},
        {"property": "og:title", "content": page_title},
        {"property": "og:type", "content": "website"},
        {"property": "og:description", "content": app_description},
        {"property": "og:image", "content": app_image},
    ]


dash.register_page(
    __name__,
    path_template="/analysis/<analysis_id>",
    path="/analysis",
    name=page_title,
    meta_tags=metas,
)


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
                dcc.Store(id="xiv-gear-sheet-data"),
                dcc.Store(id="fflogs-encounter"),
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

        valid_analysis_id = check_valid_player_analysis_id(analysis_id)

        # Message to display if something goes wrong.
        error_children = []

        # redirect to 404 if no analysis page exists
        if not valid_analysis_id:
            error_children.extend(
                [
                    html.H2("404 Not Found"),
                    html.P(
                        [
                            "The link entered does not exist. ",
                            html.A("Click here", href="/"),
                            " to return home and analyze a rotation.",
                        ]
                    ),
                ]
            )
            return html.Div(error_children)

        # Read in encounter info

        analysis_details = retrieve_player_analysis_information(analysis_id)
        #### Job build / Etro card setup ####
        job_build_url = reconstruct_job_build_url(
            analysis_details["job_build_id"], analysis_details["job_build_provider"]
        )

        #### FFLogs Card Info ####
        # FFlogs URL
        report_id = analysis_details["report_id"]
        fight_id = analysis_details["fight_id"]
        fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"

        # Encounter Info
        boss_name = analysis_details["encounter_name"]
        fight_duration = format_kill_time_str(analysis_details["kill_time"])
        encounter_name_time = f"{boss_name} ({fight_duration})"
        # Job selection info

        # Player information
        # There's a 50% chance the wrong character will be reported
        # if you have two characters with the same name on the same job
        character = analysis_details["player_name"]
        player_id = analysis_details["player_id"]
        role = analysis_details["role"]
        encounter_id = analysis_details["encounter_id"]
        fight_phase = analysis_details["phase_id"]
        furthest_phase = analysis_details["last_phase_index"]
        level = encounter_level[encounter_id]

        redo_rotation = analysis_details["redo_rotation_flag"]
        recompute_pdf_flag = analysis_details["redo_dps_pdf_flag"]

        # Player stat info
        main_stat = int(analysis_details["main_stat"])
        main_stat_pre_bonus = analysis_details["main_stat_pre_bonus"]
        secondary_stat_pre_bonus = analysis_details["secondary_stat_pre_bonus"]
        secondary_stat = analysis_details["secondary_stat"]
        determination = analysis_details["determination"]
        speed_stat = analysis_details["speed"]
        crit = analysis_details["critical_hit"]
        direct_hit = analysis_details["direct_hit"]
        weapon_damage = analysis_details["weapon_damage"]
        delay = analysis_details["delay"]

        party_bonus = analysis_details["party_bonus"]
        player_job_no_space = analysis_details["job"]
        player_id = int(analysis_details["player_id"])
        pet_ids = analysis_details["pet_ids"]

        # Get actions and create a rotation again, used if the RotationTable class updates.
        if redo_rotation:
            try:
                rotation_object = RotationTable(
                    headers,
                    analysis_details["report_id"],
                    int(analysis_details["fight_id"]),
                    player_job_no_space,
                    player_id,
                    crit,
                    direct_hit,
                    determination,
                    level,
                    fight_phase,
                    damage_buff_table,
                    critical_hit_rate_table,
                    direct_hit_rate_table,
                    guaranteed_hits_by_action_table,
                    guaranteed_hits_by_buff_table,
                    potency_table,
                    encounter_phases,
                    pet_ids,
                    analysis_details["excluded_enemy_ids"],
                )

                action_df = rotation_object.filtered_actions_df
                rotation_df = rotation_object.rotation_df

                with open(BLOB_URI / f"rotation-object-{analysis_id}.pkl", "wb") as f:
                    pickle.dump(rotation_object, f)
                unflag_redo_rotation(analysis_id)

            # FIXME: medication amt remove
            # Catch any errors and notify user
            except Exception as e:
                error_info = (
                    report_id,
                    fight_id,
                    player_id,
                    encounter_id,
                    "Unavailable",
                    fight_phase,
                    player_job_no_space,
                    "N/A",
                    int(main_stat_pre_bonus),
                    int(main_stat),
                    "Main",
                    secondary_stat_pre_bonus,
                    secondary_stat,
                    None,
                    int(determination),
                    int(speed_stat),
                    int(crit),
                    int(direct_hit),
                    int(weapon_damage),
                    delay,
                    -1,
                    party_bonus,
                    str(e),
                    traceback.format_exc(),
                )
                insert_error_player_analysis(*error_info)
                error_children.append(error_alert(str(e)))
                return error_children
        else:
            try:
                with open(
                    BLOB_URI / f"rotation-object-{analysis_id}.pkl", "rb"
                ) as outp:
                    rotation_object = pickle.load(outp)
                if "filtered_actions_df" in rotation_object.__dict__.keys():
                    action_df = rotation_object.filtered_actions_df
                else:
                    action_df = rotation_object.actions_df
                    action_df = action_df[
                        ~action_df["targetID"].isin(
                            analysis_details["excluded_enemy_ids"]
                        )
                    ]

                rotation_df = rotation_object.rotation_df

            except Exception as e:
                error_children.append(
                    html.P(f"The following error was encountered: {str(e)}")
                )
                return html.Div(error_children)

        # Recompute DPS distributions if flagged to do so.
        # Happens if `ffxiv_stats` updates with some sort of correction.
        if recompute_pdf_flag:
            try:
                job_analysis_object = rotation_analysis(
                    role,
                    player_job_no_space,
                    rotation_df,
                    rotation_object.fight_dps_time,
                    main_stat,
                    secondary_stat,
                    determination,
                    speed_stat,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    main_stat_pre_bonus,
                    level=level,
                )

                job_analysis_data = job_analysis_to_data_class(
                    job_analysis_object, job_analysis_object.t
                )

                with open(BLOB_URI / f"job-analysis-data-{analysis_id}.pkl", "wb") as f:
                    pickle.dump(job_analysis_data, f)
                unflag_report_recompute(analysis_id)

            # FIXME: medication amt remove (-1)
            # Catch any errors and notify user
            except Exception as e:
                error_info = (
                    report_id,
                    fight_id,
                    player_id,
                    encounter_id,
                    "Unavailable",
                    fight_phase,
                    player_job_no_space,
                    "N/A",
                    int(main_stat_pre_bonus),
                    int(main_stat),
                    "Main",
                    secondary_stat_pre_bonus,
                    secondary_stat,
                    None,
                    int(determination),
                    int(speed_stat),
                    int(crit),
                    int(direct_hit),
                    int(weapon_damage),
                    delay,
                    -1,
                    party_bonus,
                    str(e),
                    traceback.format_exc(),
                )
                insert_error_player_analysis(*error_info)
                error_children.append(error_alert(str(e)))
                return error_children
        else:
            try:
                with open(
                    BLOB_URI / f"job-analysis-data-{analysis_id}.pkl", "rb"
                ) as outp:
                    job_analysis_data = pickle.load(outp)

            except Exception as e:
                error_children.append(
                    html.P(f"The following error was encountered: {str(e)}")
                )
                return html.Div(error_children)

        # DPS of each action + the entire rotation

        action_dps = (
            action_df[["ability_name", "amount"]].groupby("ability_name").sum()
            / job_analysis_data.active_dps_t
        ).reset_index()
        rotation_dps = action_dps["amount"].sum()
        rotation_percentile = (
            get_dps_dmg_percentile(
                rotation_dps
                * job_analysis_data.active_dps_t
                / job_analysis_data.analysis_t,
                job_analysis_data.rotation_dps_distribution,
                job_analysis_data.rotation_dps_support,
            )
            / 100
        )

        ### make rotation card results
        rotation_fig = make_rotation_pdf_figure(
            job_analysis_data,
            rotation_dps,
            job_analysis_data.active_dps_t,
            job_analysis_data.analysis_t,
        )
        rotation_graph = (
            dcc.Graph(
                figure=rotation_fig,
                id="rotation-pdf-fig",
            ),
        )

        rotation_percentile_table = make_rotation_percentile_table(
            job_analysis_data, rotation_percentile
        )

        ### make action card results
        action_fig = make_action_pdfs_figure(
            job_analysis_data,
            action_dps,
            job_analysis_data.active_dps_t,
            job_analysis_data.analysis_t,
        )

        new_action_fig = make_action_box_and_whisker_figure(
            job_analysis_data,
            action_dps,
            job_analysis_data.active_dps_t,
            job_analysis_data.analysis_t,
        )

        action_graph = [dcc.Graph(figure=action_fig, id="action-pdf-fig")]
        action_graph = [dcc.Graph(figure=new_action_fig, id="action-pdf-fig-new")]

        # action_summary_table = make_action_table(job_analysis_data, action_df)

        rotation_graph = rotation_graph[0]
        rotation_percentile_table = rotation_percentile_table[0]
        action_graph = action_graph[0]
        # action_summary_table = action_summary_table[0]

        # action_options = action_dps["ability_name"].tolist()
        # action_values = action_dps["ability_name"].tolist()

        # Crit result text
        crit_text = rotation_percentile_text_map(rotation_percentile)
        crit_text += f" Your DPS corresponded to the {rotation_percentile:0.1%} percentile of the DPS distribution. Scroll down to see a detailed analysis of your rotation. Please note that DPS is reported and not rDPS (or any of the derived DPS metrics) and that this percentile has no relation to percentiles reported on FFLogs."

        # Give warning if not all variance in a job is supported (AST, BRD, DNC)
        if player_job_no_space in job_warnings.keys():
            alert_child = dbc.Alert(
                [
                    html.I(className="bi bi-exclamation-triangle-fill me-2"),
                    job_warnings[player_job_no_space],
                ],
                color="warning",
                className="d-flex align-items-center",
            )
        else:
            alert_child = []

        xiv_analysis_url = (
            f"https://xivanalysis.com/fflogs/{report_id}/{fight_id}/{player_id}"
        )

        job_radio_options = show_job_options(
            get_player_analysis_job_records(report_id, fight_id),
            role,
            rotation_object.fight_start_time,
        )
        job_radio_options_dict = {
            "Tank": job_radio_options[0],
            "Healer": job_radio_options[1],
            "Melee": job_radio_options[2],
            "Physical Ranged": job_radio_options[3],
            "Magical Ranged": job_radio_options[4],
        }
        job_radio_value_dict = {
            "Tank": None,
            "Healer": None,
            "Melee": None,
            "Physical Ranged": None,
            "Magical Ranged": None,
        }

        job_radio_value_dict[role] = player_id

        ### Make all the divs
        job_build = initialize_job_build(
            job_build_url,
            role,
            main_stat_pre_bonus,
            secondary_stat_pre_bonus,
            determination,
            speed_stat,
            crit,
            direct_hit,
            weapon_damage,
        )

        phase_select_options, phase_select_hidden = get_phase_selector_options(
            furthest_phase, encounter_id
        )
        fflogs_card = initialize_fflogs_card(
            fflogs_url,
            encounter_name_time,
            phase_select_options,
            fight_phase,
            phase_select_hidden,
            job_radio_options_dict,
            job_radio_value_dict,
            False,
            False,
        )
        rotation_card = initialize_rotation_card(
            rotation_graph, rotation_percentile_table
        )
        # action_card = initialize_action_card(
        #     action_graph, action_summary_table, action_options, action_values
        # )
        action_card = initialize_new_action_card(action_graph)
        result_card = initialize_results(
            character,
            crit_text,
            alert_child,
            rotation_card,
            action_card,
            analysis_url,
            xiv_analysis_url,
            False,
        )

        access_db_row = (analysis_id, datetime.datetime.now())
        # update access table
        if not DRY_RUN:
            update_access_table(access_db_row)

        return dash.html.Div(
            [
                dcc.Store(id="xiv-gear-sheet-data"),
                dcc.Store(id="fflogs-encounter"),
                job_build,
                html.Br(),
                fflogs_card,
                html.Br(),
                result_card,
            ]
        )


@callback(
    Output("bottom-build-row", "hidden"),
    Input("role-select", "value"),
)
def display_bottom_build_row(role: str) -> bool:
    """Display the bottom job build row for Tanks, allowing Tenacity to be inputted.

    Args:
        role (str): Selected Role

    Returns:
        bool: Whether to display the stat row or not.
    """
    if role == "Tank":
        return False
    else:
        return True


@callback(
    Output("main-stat-label", "children"),
    Output("main-stat", "placeholder"),
    Output("speed-tooltip", "children"),
    Output("speed-stat", "placeholder"),
    Input("role-select", "value"),
)
def fill_role_stat_labels(role: str) -> tuple[str, str, str, str]:
    """
    Fill the role stat labels and placeholders based on the selected role.

    Parameters:
    role (str): Selected Role.

    Returns:
    tuple[str, str, str, str]: The main stat label, main stat placeholder, speed tooltip, and speed stat placeholder.
    """
    if role == "Unsupported":
        raise PreventUpdate

    return (
        role_stat_dict[role]["main_stat"]["label"],
        role_stat_dict[role]["main_stat"]["placeholder"],
        role_stat_dict[role]["speed_stat"]["label"],
        role_stat_dict[role]["speed_stat"]["placeholder"],
    )


@callback(
    Output("job-build-url-feedback", "children"),
    Output("xiv-gear-set-div", "hidden"),
    Output("job-build-url", "valid"),
    Output("job-build-url", "invalid"),
    Output("job-build-name-div", "children", allow_duplicate=True),
    Output("role-select", "value"),
    Output("main-stat", "value"),
    Output("DET", "value"),
    Output("speed-stat", "value"),
    Output("CRT", "value"),
    Output("DH", "value"),
    Output("WD", "value"),
    Output("TEN", "value"),
    Output("xiv-gear-sheet-data", "data"),
    Input("job-build-url-button", "n_clicks"),
    State("job-build-url", "value"),
    State("role-select", "value"),
    prevent_initial_call=True,
)
def process_job_build_url(
    n_clicks: int, url: str, selected_role: str
) -> tuple[Any, ...]:
    """
    Get the report/fight ID from an etro.gg/xivgear.app URL, then determine the encounter ID, start time, and jobs present.

    Parameters:
    n_clicks (int): Number of times the button has been clicked.
    url (str): The xivgear/etro.gg URL to process.
    default_role (str): The default role to select.

    Returns:
    tuple[Any, ...]: A tuple containing the feedback, validity, build name, role, stats, and warning message.
    """
    if n_clicks is None:
        raise PreventUpdate

    invalid_return = [
        True,
        False,
        True,
        [],
        selected_role,
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        {"gear_index": -1, "data": []},
    ]

    # Check if job build is etro or xivgear
    valid_provider, provider = job_build_provider(url)

    if not valid_provider:
        return tuple([provider] + invalid_return)

    elif provider == "etro.gg":
        # Get the build if everything checks out
        (
            job_build_call_successful,
            feedback,
            hide_xiv_gear_set_selector,
            job_build_valid,
            job_build_invalid,
            build_name_html,
            selected_role,
            primary_stat,
            determination,
            speed,
            ch,
            dh,
            wd,
            tenacity,
            gear_set_store,
        ) = etro_build(url)

    # xivgear is more complicated because it returns sheets with multiple jobs.
    # Also create a new dropdown with the different options
    elif provider == "xivgear.app":
        (
            job_build_call_successful,
            feedback,
            hide_xiv_gear_set_selector,
            job_build_valid,
            job_build_invalid,
            build_name_html,
            selected_role,
            primary_stat,
            determination,
            speed,
            ch,
            dh,
            wd,
            tenacity,
            gear_set_store,
        ) = xiv_gear_build(url)

    if not job_build_call_successful:
        return tuple([feedback] + invalid_return)

    return (
        [],
        hide_xiv_gear_set_selector,
        job_build_valid,
        job_build_invalid,
        build_name_html,
        selected_role,
        primary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        tenacity,
        gear_set_store,
    )


@callback(
    Output("xiv-gear-select", "options"),
    Output("xiv-gear-select", "value"),
    Input("xiv-gear-sheet-data", "data"),
)
def fill_xiv_gear_build_selector(data):
    if (data is None) or (not data):
        raise PreventUpdate
    gear_data = data["data"]
    gear_idx = data["gear_index"]
    # Don't select anything if a gearset wasn't explicitly provided
    gear_idx = None if gear_idx == -1 else str(gear_idx)
    selector_options = [
        {"label": d[1], "value": str(idx)} for idx, d in enumerate(gear_data)
    ]
    return selector_options, gear_idx


@callback(
    Output("job-build-name-div", "children", allow_duplicate=True),
    Output("main-stat", "value", allow_duplicate=True),
    Output("DET", "value", allow_duplicate=True),
    Output("speed-stat", "value", allow_duplicate=True),
    Output("CRT", "value", allow_duplicate=True),
    Output("DH", "value", allow_duplicate=True),
    Output("WD", "value", allow_duplicate=True),
    Output("TEN", "value", allow_duplicate=True),
    Input("xiv-gear-sheet-data", "data"),
    Input("xiv-gear-select", "value"),
    prevent_initial_call=True,
)
def fill_job_build_via_xiv_gear_select(xiv_gear_sheet_data, index):
    if index is None:
        raise PreventUpdate
    index = int(index)
    if index == -1:
        raise PreventUpdate
    gear_fill = xiv_gear_sheet_data["data"][index]

    job_build_name = [html.H4(f"Build name: {gear_fill[1]}")]
    return tuple(job_build_name + gear_fill[3:])


@callback(
    Output("fflogs-card", "hidden"),
    Input("main-stat", "valid"),
    Input("TEN", "valid"),
    Input("DET", "valid"),
    Input("speed-stat", "valid"),
    Input("CRT", "valid"),
    Input("DH", "valid"),
    Input("WD", "valid"),
)
def job_build_defined(
    main_stat: bool,
    tenacity: bool,
    determination: bool,
    speed: bool,
    crit: bool,
    direct_hit: bool,
    weapon_damage: bool,
) -> bool:
    """
    Check if any job build elements are missing/invalid, hide everything else if they are.

    Parameters:
    main_stat (bool): Validity of the main stat.
    tenacity (bool): Validity of the tenacity stat.
    determination (bool): Validity of the determination stat.
    speed (bool): Validity of the speed stat.
    crit (bool): Validity of the critical hit stat.
    direct_hit (bool): Validity of the direct hit stat.
    weapon_damage (bool): Validity of the weapon damage stat.

    Returns:
    bool: Whether to hide the fflogs card or not.
    """
    return not all(
        [
            main_stat,
            tenacity,
            determination,
            speed,
            crit,
            direct_hit,
            weapon_damage,
        ]
    )


@callback(
    Output("fflogs-url-feedback", "children"),
    Output("encounter-name-time", "children"),
    Output("phase-select", "options"),
    Output("phase-select-div", "hidden"),
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
    Output("encounter-info", "hidden"),
    Output("fflogs-encounter", "data"),
    Input("fflogs-url-state", "n_clicks"),
    State("fflogs-url", "value"),
    State("role-select", "value"),
    State("fflogs-encounter", "data"),
    prevent_initial_call=True,
)
def process_fflogs_url(n_clicks, url, role, fflogs_data):
    """Get the report/fight ID from an fflogs URL, then determine the encounter ID, start time, and jobs present."""

    if url is None:
        raise PreventUpdate
    radio_value = None
    error_return = [
        [],
        [],
        True,
        [],
        [],
        radio_value,
        [],
        radio_value,
        [],
        radio_value,
        [],
        radio_value,
        [],
        radio_value,
        False,
        True,
        True,
        fflogs_data,
    ]

    report_id, fight_id, error_message = parse_fflogs_url(url)
    if error_message != "":
        return tuple([error_message] + error_return)

    (
        error_message,
        fight_id,
        encounter_id,
        start_time,
        job_information,
        limit_break_information,
        kill_time,
        encounter_name,
        start_time,
        furthest_phase_index,
        excluded_enemy_ids,
    ) = encounter_information(report_id, fight_id)

    if error_message != "":
        return tuple([error_message] + error_return)

    fight_time_str = format_kill_time_str(kill_time)

    # Encounter info
    # If there's phase info, also make a selector for that.
    # Otherwise, have a mostly empty selector that's hidden
    phase_select_options, phase_select_hidden = get_phase_selector_options(
        furthest_phase_index, encounter_id
    )

    # Display the encounter name and kill time as H3 header
    encounter_name_time = f"{encounter_name} ({fight_time_str})"

    if encounter_id not in valid_encounters:
        feedback_text = html.Span(
            [
                f"Sorry, {encounter_name} is not supported. Please check the supported encounters ",
                html.A(
                    "here.",
                    target="_blank",
                    href="/compatibility",
                    style={"color": "#e74c3a"},
                ),
            ]
        )
        return tuple([feedback_text] + error_return)

    (
        tank_radio_items,
        healer_radio_items,
        melee_radio_items,
        physical_ranged_radio_items,
        magical_ranged_radio_items,
    ) = show_job_options(job_information, role, start_time)

    db_rows = [
        (
            report_id,
            fight_id,
            encounter_id,
            furthest_phase_index,
            encounter_name,
            kill_time,
            k["player_name"],
            k["player_server"],
            k["player_id"],
            k["pet_ids"],
            excluded_enemy_ids,
            k["job"],
            k["role"],
        )
        for k in job_information
    ]
    if not DRY_RUN:
        update_encounter_table(db_rows)

    fflogs_data = {"fight_id": fight_id, "report_id": report_id}

    return (
        [],
        encounter_name_time,
        phase_select_options,
        phase_select_hidden,
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
        False,
        fflogs_data,
    )


@callback(
    Output("tank-jobs", "options", allow_duplicate=True),
    Output("tank-jobs", "value", allow_duplicate=True),
    Output("healer-jobs", "options", allow_duplicate=True),
    Output("healer-jobs", "value", allow_duplicate=True),
    Output("melee-jobs", "options", allow_duplicate=True),
    Output("melee-jobs", "value", allow_duplicate=True),
    Output("physical-ranged-jobs", "options", allow_duplicate=True),
    Output("physical-ranged-jobs", "value", allow_duplicate=True),
    Output("magical-ranged-jobs", "options", allow_duplicate=True),
    Output("magical-ranged-jobs", "value", allow_duplicate=True),
    Input("role-select", "value"),
    State("tank-jobs", "options"),
    State("tank-jobs", "value"),
    State("healer-jobs", "options"),
    State("healer-jobs", "value"),
    State("melee-jobs", "options"),
    State("melee-jobs", "value"),
    State("physical-ranged-jobs", "options"),
    State("physical-ranged-jobs", "value"),
    State("magical-ranged-jobs", "options"),
    State("magical-ranged-jobs", "value"),
    prevent_initial_call=True,
)
def update_player_job_selector(
    selected_role: str,
    tank_jobs: list,
    tank_values: list,
    healer_jobs: list,
    healer_values: list,
    melee_jobs: list,
    melee_values: list,
    phys_ranged_jobs: list,
    phys_ranged_values: list,
    caster_jobs: list,
    caster_values: list,
) -> tuple:
    """
    Update job selectors by enabling the jobs of the selected role and disabling others.

    Additionally, preserve the value list for the selected role and set others to None.

    Args:
        selected_role (str): The currently selected job role (e.g., "Tank", "Healer").
        tank_jobs (list): List of Tank job dictionaries.
        tank_values (list): Selected values for Tank jobs.
        healer_jobs (list): List of Healer job dictionaries.
        healer_values (list): Selected values for Healer jobs.
        melee_jobs (list): List of Melee job dictionaries.
        melee_values (list): Selected values for Melee jobs.
        phys_ranged_jobs (list): List of Physical Ranged job dictionaries.
        phys_ranged_values (list): Selected values for Physical Ranged jobs.
        caster_jobs (list): List of Magical Ranged job dictionaries.
        caster_values (list): Selected values for Magical Ranged jobs.

    Returns:
        tuple: Updated job lists and their corresponding values with 'disabled' flags set.
    """
    # Define a mapping of roles to their respective job lists
    role_to_jobs = {
        "Tank": tank_jobs,
        "Healer": healer_jobs,
        "Melee": melee_jobs,
        "Physical Ranged": phys_ranged_jobs,
        "Magical Ranged": caster_jobs,
    }

    role_to_values = {
        "Tank": tank_values,
        "Healer": healer_values,
        "Melee": melee_values,
        "Physical Ranged": phys_ranged_values,
        "Magical Ranged": caster_values,
    }

    # Iterate over each role and its job list
    for role, jobs in role_to_jobs.items():
        # Determine if the current role is the selected role
        is_selected = role == selected_role

        # Update the 'disabled' status for each job in the current role
        for job in jobs:
            job["disabled"] = not is_selected

    # Iterate over each role's values to preserve selected role's values and set others to None
    for role, values in role_to_values.items():
        if role != selected_role:
            role_to_values[role] = None
        # If it's the selected role, keep the values as is
        # (No action needed)

    # Return the updated job lists and their corresponding value lists in the specified order
    return (
        tank_jobs,
        role_to_values["Tank"],
        healer_jobs,
        role_to_values["Healer"],
        melee_jobs,
        role_to_values["Melee"],
        phys_ranged_jobs,
        role_to_values["Physical Ranged"],
        caster_jobs,
        role_to_values["Magical Ranged"],
    )


@callback(
    Output("compute-dmg-div", "hidden"),
    Input("healer-jobs", "options"),
    Input("tank-jobs", "options"),
    Input("melee-jobs", "options"),
    Input("physical-ranged-jobs", "options"),
    Input("magical-ranged-jobs", "options"),
    Input("healer-jobs", "value"),
    Input("tank-jobs", "value"),
    Input("melee-jobs", "value"),
    Input("physical-ranged-jobs", "value"),
    Input("magical-ranged-jobs", "value"),
)
def display_compute_button(
    healers: list[dict[str, Any]],
    tanks: list[dict[str, Any]],
    melees: list[dict[str, Any]],
    phys_ranged: list[dict[str, Any]],
    magic_ranged: list[dict[str, Any]],
    healer_value: str | None,
    tank_value: str | None,
    melee_value: str | None,
    phys_ranged_value: str | None,
    magic_ranged_value: str | None,
) -> bool:
    """
    Display button to compute DPS distributions once a job is selected.

    Otherwise, no button is shown.

    Parameters:
    healers (list[dict[str, Any]]): List of healer job options.
    tanks (list[dict[str, Any]]): List of tank job options.
    melees (list[dict[str, Any]]): List of melee job options.
    phys_ranged (list[dict[str, Any]]): List of physical ranged job options.
    magic_ranged (list[dict[str, Any]]): List of magical ranged job options.
    healer_value (str | None): Selected healer job.
    tank_value (str | None): Selected tank job.
    melee_value (str | None): Selected melee job.
    phys_ranged_value (str | None): Selected physical ranged job.
    magic_ranged_value (str | None): Selected magical ranged job.

    Returns:
    bool: Whether to hide the compute button or not.
    """
    # Handle None values for job lists
    healers = [] if healers is None else healers
    tanks = [] if tanks is None else tanks
    melees = [] if melees is None else melees
    phys_ranged = [] if phys_ranged is None else phys_ranged
    magic_ranged = [] if magic_ranged is None else magic_ranged

    job_list = healers + tanks + melees + phys_ranged + magic_ranged

    selected_job = [
        x
        for x in [
            healer_value,
            tank_value,
            melee_value,
            phys_ranged_value,
            magic_ranged_value,
        ]
        if x is not None
    ]

    if selected_job == [] or job_list == []:
        return True

    # Get just the selected job ID
    selected_job_id = selected_job[0]

    # Find the selected job in the job list and check if it's disabled
    for job in job_list:
        if job["value"] == selected_job_id:
            # If the job is disabled, hide the button
            if job.get("disabled", False):
                return True
            # Otherwise, the job is enabled and selected, show the button
            return False

    # If we get here, the selected job doesn't exist in the job list
    return True


@callback(
    Output("compute-dmg-button", "children"),
    Output("compute-dmg-button", "disabled"),
    Input("compute-dmg-button", "n_clicks"),
    prevent_initial_call=True,
)
def disable_analyze_button(n_clicks: int) -> tuple[list[Any], bool]:
    """
    Return a disabled, spiny button when the log/rotation is being analyzed.

    Parameters:
    n_clicks (int): Number of times the button has been clicked.

    Returns:
    tuple[list[Any], bool]: The button content and whether it is disabled.
    """
    if (n_clicks is None) or DEBUG:
        return ["Analyze rotation"], False
    else:
        return [dbc.Spinner(size="sm"), " Analyzing your log..."], True


@callback(
    Output("clipboard", "content"),
    Input("clipboard", "n_clicks"),
    State("analysis-link", "value"),
)
def copy_analysis_link(n: int, selected: str) -> str:
    """
    Copy analysis link to clipboard.

    Parameters:
    n (int): Number of times the clipboard button has been clicked.
    selected (str): The analysis link to copy.

    Returns:
    str: The content to be copied to the clipboard.
    """
    if selected is None:
        return "No selections"
    return selected


@callback(
    Output("url", "href", allow_duplicate=True),
    Output("compute-dmg-button", "children", allow_duplicate=True),
    Output("compute-dmg-button", "disabled", allow_duplicate=True),
    Output("crit-result-text", "children"),
    Output("results-div", "hidden"),
    Input("compute-dmg-button", "n_clicks"),
    State("main-stat", "value"),
    State("TEN", "value"),
    State("DET", "value"),
    State("speed-stat", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    State("xiv-gear-select", "value"),
    State("fflogs-encounter", "data"),
    State("fflogs-url", "value"),
    State("phase-select", "value"),
    State("job-build-url", "value"),
    Input("healer-jobs", "value"),
    Input("tank-jobs", "value"),
    Input("melee-jobs", "value"),
    Input("physical-ranged-jobs", "value"),
    Input("magical-ranged-jobs", "value"),
    prevent_initial_call=True,
)
def analyze_and_register_rotation(
    n_clicks: int,
    main_stat_pre_bonus: int,
    tenacity: int,
    determination: int,
    speed_stat: int,
    ch: int,
    dh: int,
    wd: int,
    job_build_idx,
    fflogs_encounter_data: dict | None,
    fflogs_url: str,
    fight_phase: int | None,
    job_build_url: str,
    healer_jobs: str | None = None,
    tank_jobs: str | None = None,
    melee_jobs: str | None = None,
    phys_ranged_jobs: str | None = None,
    magical_jobs: str | None = None,
) -> tuple[Any, ...]:
    """
    Analyze and register the rotation based on the provided inputs.

    Parameters:
    n_clicks (int): Number of times the button has been clicked.
    main_stat_pre_bonus (int): Main stat value before bonus.
    tenacity (int): Tenacity stat value.
    determination (int): Determination stat value.
    speed_stat (int): Speed stat value.
    ch (int): Critical hit stat value.
    dh (int): Direct hit stat value.
    wd (int): Weapon damage stat value.
    fflogs_url (str): FFLogs URL.
    fight_phase (Optional[int]): Selected fight phase.
    job_build_url (str): Etro URL.
    healer_jobs (Optional[str]): Selected healer job.
    tank_jobs (Optional[str]): Selected tank job.
    melee_jobs (Optional[str]): Selected melee job.
    phys_ranged_jobs (Optional[str]): Selected physical ranged job.
    magical_jobs (Optional[str]): Selected magical ranged job.

    Returns:
    tuple[Any, ...]: A tuple containing the updated URL, button content, button disabled state, result text, and results div hidden state.
    """
    updated_url = dash.no_update

    player_id = [healer_jobs, tank_jobs, melee_jobs, phys_ranged_jobs, magical_jobs]

    if n_clicks is None:
        raise PreventUpdate

    if isinstance(fight_phase, list):
        fight_phase = fight_phase[0]
    else:
        fight_phase = int(fight_phase)

    # Noticed this was causing errors by selecting from empty list
    # Couldn't repro, but it's easy to check.
    player_id = [x for x in player_id if x is not None]
    if len(player_id) == 0:
        return (
            updated_url,
            ["Analyze rotation"],
            False,
            [error_alert("No player selected.")],
            False,
        )

    player_id = player_id[0]
    try:
        report_id = fflogs_encounter_data["report_id"]
        fight_id = fflogs_encounter_data["fight_id"]
        error_message = ""
    except Exception:
        report_id, fight_id, error_message = parse_fflogs_url(fflogs_url)

        if fight_id == "last":
            fight_id, error_message = _query_last_fight_id(report_id)

    if error_message != "":
        return (
            updated_url,
            ["Analyze rotation"],
            False,
            [error_alert(error_message)],
            False,
        )
    (
        player_name,
        pet_ids,
        excluded_enemy_ids,
        job_no_space,
        role,
        encounter_id,
        encounter_name,
        last_phase_index,
    ) = read_player_analysis_info(report_id, fight_id, player_id)

    # This happens if the log URL is changed, but not submitted.
    if player_name is None:
        return (
            updated_url,
            ["Analyze rotation"],
            False,
            [error_alert("Please resubmit Log URL, linked log changed.")],
            False,
        )
    # Edge case example: fight analyzing phase 5 is loaded
    # user switches log url to a phase where phase 1 was reached
    # if they don't hit submit, phase 5 can still be selected, which is
    # impossible. Easy solution:
    # Just analyze the final phase reached, that's pry what they wanted anw.
    if fight_phase > last_phase_index:
        fight_phase = last_phase_index

    # FIXME: remove
    medication_amt = -1

    level = encounter_level[encounter_id]

    # Higher level = bigger damage = bigger discretization step size
    delta_map = {90: 4, 100: 9}

    main_stat_multiplier = compute_party_bonus(report_id, fight_id)
    main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"].lower()
    main_stat = int(main_stat_pre_bonus * main_stat_multiplier)

    secondary_stat_type, secondary_stat_pre_bonus, secondary_stat = set_secondary_stats(
        role, abbreviated_job_map[job_no_space].upper(), main_stat_multiplier, tenacity
    )
    delay = weapon_delays[abbreviated_job_map[job_no_space].upper()]

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
        if (job_build_url != "") & (job_build_url is not None):
            job_build_id, job_build_provider = parse_build_uuid(
                job_build_url, job_build_idx
            )
        else:
            job_build_id = None
            job_build_provider = None
        # Check if the rotation has been analyzed before
        prior_analysis_id, redo_analysis = search_prior_player_analyses(
            report_id,
            fight_id,
            fight_phase,
            job_no_space,
            player_name,
            main_stat_pre_bonus,
            secondary_stat_pre_bonus,
            determination,
            speed_stat,
            ch,
            dh,
            wd,
            delay,
        )

        # redirect if it has and doesn't need to be redone
        if (prior_analysis_id is not None) and (not redo_analysis):
            return (
                f"/analysis/{prior_analysis_id}",
                ["Analyze rotation"],
                False,
                [],
                False,
            )

        # if n_prior_reports == 0:
        rotation = RotationTable(
            headers,
            report_id,
            fight_id,
            job_no_space,
            player_id,
            ch,
            dh,
            determination,
            level,
            fight_phase,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            encounter_phases,
            pet_ids,
            excluded_enemy_ids,
        )

        rotation_df = rotation.rotation_df
        t = rotation.fight_dps_time
        encounter_name = rotation.fight_name

        job_analysis_object = rotation_analysis(
            role,
            job_no_space,
            rotation_df,
            t,
            main_stat,
            secondary_stat,
            determination,
            speed_stat,
            ch,
            dh,
            wd,
            delay,
            main_stat_pre_bonus,
            action_delta=delta_map[level],
            level=level,
        )

        job_analysis_data = job_analysis_to_data_class(job_analysis_object, t)
        job_analysis_data.interpolate_distributions()

        analysis_id = str(uuid4())
        redo_rotation_flag = 0
        redo_dps_pdf_flag = 0

        if not DRY_RUN:
            with open(BLOB_URI / f"rotation-object-{analysis_id}.pkl", "wb") as f:
                pickle.dump(rotation, f)
            with open(BLOB_URI / f"job-analysis-data-{analysis_id}.pkl", "wb") as f:
                pickle.dump(job_analysis_data, f)

            # FIXME: remove medication amt
            db_row = (
                analysis_id,
                report_id,
                fight_id,
                fight_phase,
                encounter_name,
                t,
                job_no_space,
                player_name,
                int(main_stat_pre_bonus),
                int(main_stat),
                main_stat_type,
                secondary_stat_pre_bonus,
                secondary_stat,
                secondary_stat_type,
                int(determination),
                int(speed_stat),
                int(ch),
                int(dh),
                int(wd),
                delay,
                medication_amt,
                main_stat_multiplier,
                job_build_id,
                job_build_provider,
                redo_dps_pdf_flag,
                redo_rotation_flag,
            )
            update_report_table(db_row)
            update_player_analysis_creation_table(
                (analysis_id, datetime.datetime.now())
            )
        del job_analysis_object

    # Catch any error and display it, then reset the button/prompt
    # FIXME: remove medication amt
    except Exception as e:
        error_info = (
            report_id,
            fight_id,
            player_id,
            encounter_id,
            encounter_name,
            fight_phase,
            job_no_space,
            player_name,
            int(main_stat_pre_bonus),
            int(main_stat),
            main_stat_type,
            secondary_stat_pre_bonus,
            secondary_stat,
            secondary_stat_type,
            int(determination),
            int(speed_stat),
            int(ch),
            int(dh),
            int(wd),
            delay,
            medication_amt,
            main_stat_multiplier,
            str(e),
            traceback.format_exc(),
        )

        insert_error_player_analysis(*error_info)

        return (
            updated_url,
            ["Analyze rotation"],
            False,
            [error_alert(str(e))],
            False,
        )
    updated_url = f"/analysis/{analysis_id}"
    return (updated_url, ["Analyze rotation"], False, [], False)


@callback(
    Output("main-stat", "valid"),
    Output("main-stat", "invalid"),
    Input("main-stat", "value"),
)
def valid_main_stat(main_stat_value: int) -> tuple[bool, bool]:
    """
    Validate the main stat input.

    Parameters:
    main_stat_value (int): The value of the main stat to validate.

    Returns:
    tuple[bool, bool]: A tuple containing the validation results for the main stat.
    """
    if main_stat_value is None:
        raise PreventUpdate
    if validate_meldable_stat(
        "test",
        main_stat_value,
        stat_ranges["main_stat"]["lower"],
        stat_ranges["main_stat"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(Output("DET", "valid"), Output("DET", "invalid"), Input("DET", "value"))
def valid_determination(determination: int) -> tuple[bool, bool]:
    """
    Validate the determination stat input.

    Parameters:
    determination (int): The value of the determination stat to validate.

    Returns:
    tuple[bool, bool]: A tuple containing the validation results for the determination stat.
    """
    if determination is None:
        raise PreventUpdate
    if validate_meldable_stat(
        "test",
        determination,
        stat_ranges["DET"]["lower"],
        stat_ranges["DET"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(
    Output("speed-stat", "valid"),
    Output("speed-stat", "invalid"),
    Input("speed-stat", "value"),
)
def valid_speed(speed: int) -> tuple:
    """
    Validate the speed stat input.

    Parameters:
    speed (int): The value of the speed stat to validate.

    Returns:
    tuple: A tuple containing the validation results for the speed stat.
    """
    if speed is None:
        raise PreventUpdate
    if validate_meldable_stat(
        "test",
        speed,
        stat_ranges["SPEED"]["lower"],
        stat_ranges["SPEED"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(Output("CRT", "valid"), Output("CRT", "invalid"), Input("CRT", "value"))
def valid_critical_hit(critical_hit: int) -> tuple:
    """
    Validate the critical hit stat input.

    Parameters:
    critical_hit (int): The value of the critical hit stat to validate.

    Returns:
    tuple: A tuple containing the validation results for the critical hit stat.
    """
    if critical_hit is None:
        raise PreventUpdate
    if validate_meldable_stat(
        "test",
        critical_hit,
        stat_ranges["CRT"]["lower"],
        stat_ranges["CRT"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(Output("DH", "valid"), Output("DH", "invalid"), Input("DH", "value"))
def valid_direct_hit(direct_hit: int) -> tuple:
    """
    Validate the direct hit stat input.

    Parameters:
    direct_hit (int): The value of the direct hit stat to validate.

    Returns:
    tuple: A tuple containing the validation results for the direct hit stat.
    """
    if direct_hit is None:
        raise PreventUpdate
    if validate_meldable_stat(
        "test",
        direct_hit,
        stat_ranges["DH"]["lower"],
        stat_ranges["DH"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(Output("WD", "valid"), Output("WD", "invalid"), Input("WD", "value"))
def valid_weapon_damage(weapon_damage: int) -> tuple:
    """
    Validate the weapon damage stat input.

    Parameters:
    weapon_damage (int): The value of the weapon damage stat to validate.

    Returns:
    tuple: A tuple containing the validation results for the weapon damage stat.
    """
    if weapon_damage is None:
        raise PreventUpdate
    if validate_weapon_damage(weapon_damage)[0]:
        return valid_stat_return
    else:
        return invalid_stat_return


@callback(
    Output("TEN", "valid"),
    Output("TEN", "invalid"),
    Input("TEN", "value"),
    Input("role-select", "value"),
)
def valid_tenacity(tenacity: int, role: str) -> tuple:
    """
    Validate the direct hit stat input.

    Parameters:
    direct_hit (int): The value of the direct hit stat to validate.

    Returns:
    tuple: A tuple containing the validation results for the direct hit stat.
    """
    if role != "Tank":
        return valid_stat_return

    if tenacity is None:
        return invalid_stat_return

    if validate_meldable_stat(
        "test",
        tenacity,
        stat_ranges["TEN"]["lower"],
        stat_ranges["TEN"]["upper"],
    )[0]:
        return valid_stat_return
    else:
        return invalid_stat_return
