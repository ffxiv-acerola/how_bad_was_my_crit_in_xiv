# import json
# import pickle
# import time
# import traceback
# from datetime import datetime
# from typing import Any, Dict, List, Optional, Tuple, Union
# from uuid import uuid4

# import dash
# import pandas as pd
# from dash import ALL, MATCH, Input, Output, State, callback, dcc, html
# from dash.exceptions import PreventUpdate
# from plotly.graph_objs._figure import Figure

# from crit_app.config import BLOB_URI, DRY_RUN
# from crit_app.figures import (
#     make_action_box_and_whisker_figure,
#     make_kill_time_graph,
#     make_party_rotation_pdf_figure,
#     make_rotation_pdf_figure,
# )
# from crit_app.job_data.encounter_data import (
#     custom_t_clip_encounter_phases,
#     encounter_level,
#     encounter_phases,
#     skip_kill_time_analysis_phases,
#     stat_ranges,
#     valid_encounters,
# )
# from crit_app.job_data.job_data import caster_healer_strength, weapon_delays
# from crit_app.job_data.roles import (
#     abbreviated_job_map,
#     role_mapping,
#     role_stat_dict,
#     unabbreviated_job_map,
# )
# from crit_app.party_cards import (
#     create_fflogs_card,
#     create_party_accordion_children,
#     create_quick_build_table_data,
#     create_results_card,
# )
# from crit_app.shared_elements import (
#     format_kill_time_str,
#     get_phase_selector_options,
#     rotation_analysis,
#     validate_main_stat,
#     validate_meldable_stat,
#     validate_speed_stat,
#     validate_weapon_damage,
# )
# from crit_app.util.api.fflogs import (
#     _query_last_fight_id,
#     encounter_information,
#     headers,
#     limit_break_damage_events,
#     parse_fflogs_url,
# )
# from crit_app.util.api.job_build import (
#     etro_build,
#     job_build_provider,
#     parse_build_uuid,
#     xiv_gear_build,
# )
# from crit_app.util.dash_elements import error_alert
# from crit_app.util.db import (
#     check_prior_party_analysis_via_player_analyses,
#     check_valid_party_analysis_id,
#     get_party_analysis_calculation_info,
#     get_party_analysis_encounter_info,
#     get_party_analysis_player_build,
#     insert_error_party_analysis,
#     insert_error_player_analysis,
#     search_prior_player_analyses,
#     unflag_redo_rotation,
#     unflag_report_recompute,
#     update_encounter_table,
#     update_party_report_table,
#     update_player_analysis_creation_table,
#     update_report_table,
# )

# # from app import app
# from crit_app.util.history import (
#     serialize_analysis_history_record,
#     upsert_local_store_record,
# )
# from crit_app.util.party_dps_distribution import (
#     PartyRotation,
#     SplitPartyRotation,
#     kill_time_analysis,
#     rotation_dps_pdf,
# )
# from crit_app.util.player_dps_distribution import job_analysis_to_data_class
# from fflogs_rotation.job_data.data import (
#     critical_hit_rate_table,
#     damage_buff_table,
#     direct_hit_rate_table,
#     guaranteed_hits_by_action_table,
#     guaranteed_hits_by_buff_table,
#     potency_table,
# )
# from fflogs_rotation.rotation import RotationTable

# reverse_abbreviated_role_map = dict(
#     zip(abbreviated_job_map.values(), abbreviated_job_map.keys())
# )

# app = dash.get_app()
# dash.register_page(
#     __name__,
#     path_template="/party_analysis/<party_analysis_id>",
#     path="/party_analysis",
# )

# LEVEL_STEP_MAP = {
#     90: {
#         "rotation_dmg_step": 20,
#         "action_delta": 2,
#         "rotation_delta": 10,
#     },
#     100: {
#         "rotation_dmg_step": 20,
#         "action_delta": 5,
#         "rotation_delta": 15,
#     },
# }


# def layout(party_analysis_id=None):
#     if party_analysis_id is None:
#         fflogs_card = create_fflogs_card(
#             analysis_progress_children=[], analysis_progress_value=0
#         )
#         return dash.html.Div([dcc.Store(id="fflogs-party-encounter"), fflogs_card])

#     else:
#         valid_party_analysis_id = check_valid_party_analysis_id(party_analysis_id)

#         if not valid_party_analysis_id:
#             return html.Div(
#                 [
#                     html.H2("404 Not Found"),
#                     html.P(
#                         [
#                             "The link entered does not exist. ",
#                             html.A("Click here", href="/party_analysis"),
#                             " to return home and analyze a rotation.",
#                         ]
#                     ),
#                 ]
#             )
#         # Party level analysis,
#         (
#             report_id,
#             fight_id,
#             phase_id,
#             last_phase_index,
#             encounter_id,
#             encounter_name,
#             kill_time,
#             redo_analysis_flag,
#         ) = get_party_analysis_encounter_info(party_analysis_id)

#         etro_job_build_information, player_analysis_selector = (
#             get_party_analysis_player_build(party_analysis_id)
#         )

#         try:
#             with open(
#                 BLOB_URI / "party-analyses" / f"party-analysis-{party_analysis_id}.pkl",
#                 "rb",
#             ) as f:
#                 party_analysis_obj = pickle.load(f)
#         except Exception:
#             # Cant find stuff, force recompute
#             redo_analysis_flag = 1
#         ############################
#         ### FFLogs Card Elements ###
#         ############################

#         kill_time_str = format_kill_time_str(kill_time)

#         phase_selector_options, phase_select_hidden = get_phase_selector_options(
#             last_phase_index, encounter_id
#         )

#         quick_build_data = create_quick_build_table_data(etro_job_build_information)

#         party_accordion_children = create_party_accordion_children(
#             etro_job_build_information, True
#         )

#         fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"

#         # Check if analysis needs to be redone
#         if redo_analysis_flag == 1:
#             fflogs_card = create_fflogs_card(
#                 fflogs_url,
#                 encounter_name,
#                 kill_time_str,
#                 str(phase_id),
#                 phase_selector_options,
#                 phase_select_hidden,
#                 quick_build_data,
#                 party_accordion_children,
#                 hide_fflogs_div=False,
#                 force_update=True,
#                 wrap_collapse=True,
#             )
#             return html.Div([dcc.Store(id="fflogs-party-encounter"), fflogs_card])

#         # Otherwise continue
#         fflogs_card = create_fflogs_card(
#             fflogs_url,
#             encounter_name,
#             kill_time_str,
#             str(phase_id),
#             phase_selector_options,
#             phase_select_hidden,
#             quick_build_data,
#             party_accordion_children,
#             wrap_collapse=True,
#             hide_fflogs_div=False,
#             analysis_progress_children="Analysis progress: Done!",
#             analysis_progress_value=100,
#         )

#         #############################
#         ### Results Card elements ###
#         #############################

#         analysis_url = (
#             f"https://howbadwasmycritinxiv.com/party_analysis/{party_analysis_id}"
#         )
#         perform_kill_time_analysis = party_analysis_obj.perform_kill_time_analysis

#         party_dps_figure = make_party_rotation_pdf_figure(party_analysis_obj)
#         kill_time_figure = (
#             make_kill_time_graph(party_analysis_obj, kill_time)
#             if perform_kill_time_analysis
#             else None
#         )
#         player_analysis_selector_options = [
#             {
#                 "label": html.Span(
#                     [
#                         html.Span(
#                             abbreviated_job_map[x[0]],
#                             style={
#                                 "font-family": "job-icons",
#                                 "font-size": "1.2em",
#                                 "position": "relative",
#                                 "top": "3px",
#                                 "color": "#FFFFFF",
#                             },
#                         ),
#                         html.Span(" " + x[1], style={"color": "#FFFFFF"}),
#                     ],
#                     style={"align-items": "center", "justify-content": "center"},
#                 ),
#                 "value": x[2],
#             }
#             for x in player_analysis_selector
#         ]

#         results_card = create_results_card(
#             analysis_url,
#             encounter_name,
#             party_analysis_obj.fight_duration,
#             phase_id,
#             party_dps_figure,
#             perform_kill_time_analysis,
#             kill_time_figure,
#             player_analysis_selector_options,
#             player_analysis_selector[0][2],
#         )

#         return html.Div(
#             [
#                 dcc.Store(id="fflogs-party-encounter"),
#                 fflogs_card,
#                 html.Br(),
#                 results_card,
#             ]
#         )


# @callback(
#     Output("job-rotation-pdf", "figure"),
#     Input("job-selector", "value"),
#     Input("job-graph-type", "value"),
# )
# def load_job_rotation_figure(job_analysis_id: Optional[str], graph_type: str) -> Figure:
#     """
#     Load and create job rotation figure based on analysis data.

#     Args:
#         job_analysis_id: Analysis ID to load data for
#         graph_type: Type of graph to create ('rotation' or 'action')

#     Returns:
#         Plotly figure showing either rotation PDF or action box plots

#     Raises:
#         PreventUpdate: If job_analysis_id not provided
#         FileNotFoundError: If analysis data files missing
#         ValueError: If invalid graph type specified
#     """
#     if job_analysis_id is None:
#         raise PreventUpdate
#     with open(BLOB_URI / f"job-analysis-data-{job_analysis_id}.pkl", "rb") as f:
#         job_object = pickle.load(f)

#     with open(BLOB_URI / f"rotation-object-{job_analysis_id}.pkl", "rb") as f:
#         rotation_object = pickle.load(f)

#     actions_df = rotation_object.filtered_actions_df

#     action_dps = (
#         actions_df[["ability_name", "amount"]].groupby("ability_name").sum()
#         / job_object.active_dps_t
#     ).reset_index()
#     rotation_dps = action_dps["amount"].sum()

#     if graph_type == "rotation":
#         return make_rotation_pdf_figure(
#             job_object, rotation_dps, job_object.active_dps_t, job_object.analysis_t
#         )
#     else:
#         return make_action_box_and_whisker_figure(
#             job_object, action_dps, job_object.active_dps_t, job_object.analysis_t
#         )


# @callback(Output("job-level-analysis", "href"), Input("job-selector", "value"))
# def job_analysis_redirect(job_analysis_id: Optional[str]) -> str:
#     """
#     Redirect to individual analysis URL.

#     Args:
#         job_analysis_id: analysis ID to link to

#     Returns:
#         URL path string for job analysis page
#     """
#     return f"/analysis/{job_analysis_id}"


# @callback(
#     Output("party-list-collapse", "is_open"),
#     Output("party-collapse-button", "children"),
#     Input("party-collapse-button", "n_clicks"),
# )
# def toggle_party_list(n_clicks: Optional[int]) -> Tuple[bool, str]:
#     """
#     Toggle party list visibility and update button text.

#     Args:
#         n_clicks: Number of times button has been clicked

#     Returns:
#         Tuple containing:
#             - Boolean for if list should be visible
#             - String for button text
#     """
#     if n_clicks % 2 == 1:
#         return True, "Click to hide party list"
#     else:
#         return False, "Click to show party list"


# @callback(
#     Output({"type": "job-build-input", "index": ALL}, "value"),
#     # Input("quick-build-fill-button", "n_clicks"),
#     Input("quick-build-table", "data"),
#     prevent_initial_call=True,
# )
# def quick_fill_job_build(job_build_links):
#     return [e["job_build_url"] for e in job_build_links]


# @callback(
#     Output("party-clipboard", "content"),
#     Input("party-clipboard", "n_clicks"),
#     State("party-analysis-link", "value"),
# )
# def copy_party_analysis_link(n, selected):
#     """Copy analysis link to clipboard."""
#     if selected is None:
#         raise PreventUpdate
#     return selected


# @callback(
#     Output("fflogs-url-feedback2", "children"),
#     Output("fflogs-url2", "valid"),
#     Output("fflogs-url2", "invalid"),
#     Output("party-encounter-name", "children"),
#     Output("party-kill-time", "children"),
#     Output("party-phase-select", "options"),
#     Output("party-phase-select-div", "hidden"),
#     Output("quick-build-table", "data"),
#     Output("party-accordion", "children"),
#     Output("party-fflogs-hidden-div", "hidden"),
#     Output("fflogs-party-encounter", "data"),
#     Input("fflogs-url-state2", "n_clicks"),
#     State("fflogs-url2", "value"),
#     State("fflogs-party-encounter", "data"),
#     prevent_initial_call=True,
# )
# def party_fflogs_process(n_clicks, url, fflogs_data):
#     if url is None:
#         raise PreventUpdate

#     invalid_return = [False, True, [], [], [], True, [], [], True, fflogs_data]

#     report_id, fight_id, error_message = parse_fflogs_url(url)

#     if error_message != "":
#         return tuple([error_message] + invalid_return)

#     if fight_id != "last":
#         fight_id = int(fight_id)
#     (
#         error_message,
#         fight_id,
#         encounter_id,
#         start_time,
#         job_information,
#         limit_break_information,
#         kill_time,
#         encounter_name,
#         start_time,
#         furthest_phase_index,
#         excluded_enemy_ids,
#     ) = encounter_information(report_id, fight_id)

#     if error_message != "":
#         return tuple([error_message] + invalid_return)

#     if excluded_enemy_ids is not None:
#         excluded_enemy_ids = json.dumps(excluded_enemy_ids)

#     if encounter_id not in valid_encounters:
#         return tuple(
#             [f"Sorry, {encounter_name} is currently not supported."] + invalid_return
#         )

#     kill_time_str = format_kill_time_str(kill_time)

#     # Phase selection
#     phase_selector_options, phase_select_hidden = get_phase_selector_options(
#         furthest_phase_index, encounter_id
#     )

#     # Sort by job, player name so the order will always be the same
#     job_information = sorted(
#         job_information, key=lambda d: (d["job"], d["player_name"], d["player_id"])
#     )

#     quick_build_table = create_quick_build_table_data(job_information)
#     party_accordion_children = create_party_accordion_children(job_information)

#     if not DRY_RUN:
#         db_rows = [
#             (
#                 report_id,
#                 fight_id,
#                 encounter_id,
#                 furthest_phase_index,
#                 encounter_name,
#                 kill_time,
#                 k["player_name"],
#                 k["player_server"],
#                 int(k["player_id"]),
#                 k["pet_ids"],
#                 excluded_enemy_ids,
#                 k["job"],
#                 k["role"],
#             )
#             for k in job_information + limit_break_information
#         ]
#         update_encounter_table(db_rows)

#     fflogs_data = {"fight_id": fight_id, "report_id": report_id}

#     return (
#         [],
#         True,
#         False,
#         encounter_name,
#         kill_time_str,
#         phase_selector_options,
#         phase_select_hidden,
#         quick_build_table,
#         party_accordion_children,
#         False,
#         fflogs_data,
#     )


# @callback(
#     Output({"type": "tenacity-row", "index": MATCH}, "hidden"),
#     Input({"type": "main-stat-label", "index": MATCH}, "children"),
# )
# def hide_non_tank_tenactiy(main_stat_label) -> bool:
#     """Hide the Tenacity form for non-tanks.

#     Args:
#         main_stat_label (str): Main stat label used to determine role.

#     Returns:
#         bool: Whether to hide tenacity row.
#     """
#     if main_stat_label == "STR:":
#         return False
#     else:
#         return True


# @callback(
#     Output({"type": "job-build-feedback", "index": MATCH}, "children"),
#     Output({"type": "job-build-input", "index": MATCH}, "valid"),
#     Output({"type": "job-build-input", "index": MATCH}, "invalid"),
#     Output({"type": "build-name", "index": MATCH}, "children"),
#     Output(
#         {"type": "main-stat", "index": MATCH},
#         "value",
#         allow_duplicate=True,
#     ),
#     Output({"type": "DET", "index": MATCH}, "value", allow_duplicate=True),
#     Output({"type": "speed-stat", "index": MATCH}, "value", allow_duplicate=True),
#     Output({"type": "CRT", "index": MATCH}, "value", allow_duplicate=True),
#     Output({"type": "DH", "index": MATCH}, "value", allow_duplicate=True),
#     Output({"type": "WD", "index": MATCH}, "value", allow_duplicate=True),
#     Output({"type": "TEN", "index": MATCH}, "value", allow_duplicate=True),
#     Input("quick-build-fill-button", "n_clicks"),
#     State({"type": "job-build-input", "index": MATCH}, "value"),
#     State({"type": "main-stat-label", "index": MATCH}, "children"),
#     State({"type": "main-stat", "index": MATCH}, "value"),
#     State({"type": "TEN", "index": MATCH}, "value"),
#     State({"type": "DET", "index": MATCH}, "value"),
#     State({"type": "speed-stat", "index": MATCH}, "value"),
#     State({"type": "CRT", "index": MATCH}, "value"),
#     State({"type": "DH", "index": MATCH}, "value"),
#     State({"type": "WD", "index": MATCH}, "value"),
#     prevent_initial_call=True,
# )
# def job_build_process(
#     n_clicks,
#     url,
#     main_stat_label,
#     main_stat,
#     secondary_stat,
#     determination,
#     speed,
#     critical_hit,
#     direct_hit,
#     weapon_damage,
# ):
#     if n_clicks is None:
#         raise PreventUpdate
#     print(main_stat_label)

#     if main_stat_label == "STR:":
#         role = "Tank"
#     elif main_stat_label == "MND:":
#         role = "Healer"
#     elif main_stat_label == "STR/DEX:":
#         role = "Melee"
#     elif main_stat_label == "DEX:":
#         role = "Physical Ranged"
#     elif main_stat_label == "INT:":
#         role = "Magical Ranged"

#     feedback = []
#     invalid_return = [
#         False,
#         True,
#         [],
#         main_stat,
#         determination,
#         speed,
#         critical_hit,
#         direct_hit,
#         weapon_damage,
#         secondary_stat,
#     ]

#     valid_provider, provider = job_build_provider(url)
#     if not valid_provider:
#         return tuple([provider] + invalid_return)

#     elif provider == "etro.gg":
#         # Get the build if everything checks out
#         (
#             job_build_call_successful,
#             feedback,
#             hide_xiv_gear_set_selector,
#             job_build_valid,
#             job_build_invalid,
#             build_name_html,
#             selected_role,
#             main_stat,
#             determination,
#             speed,
#             critical_hit,
#             direct_hit,
#             weapon_damage,
#             tenacity,
#             _,
#         ) = etro_build(url)

#     elif provider == "xivgear.app":
#         (
#             job_build_call_successful,
#             feedback,
#             _,
#             job_build_valid,
#             job_build_invalid,
#             build_name_html,
#             selected_role,
#             main_stat,
#             determination,
#             speed,
#             critical_hit,
#             direct_hit,
#             weapon_damage,
#             tenacity,
#             _,
#         ) = xiv_gear_build(url, require_sheet_selection=True)

#     if not job_build_call_successful:
#         return tuple([feedback] + invalid_return)

#     # Make sure correct build is used
#     if selected_role != role:
#         feedback = f"A non-{role} etro build was used."
#         return tuple([feedback] + invalid_return)

#     time.sleep(0.75)
#     build_name = build_name_html[0].children
#     return (
#         feedback,
#         job_build_valid,
#         job_build_invalid,
#         f"Build name: {build_name}",
#         main_stat,
#         determination,
#         speed,
#         critical_hit,
#         direct_hit,
#         weapon_damage,
#         tenacity,
#     )


# valid_stat_return = (True, False)
# invalid_stat_return = (False, True)


# @app.callback(
#     Output({"type": "main-stat", "index": MATCH}, "valid"),
#     Output({"type": "main-stat", "index": MATCH}, "invalid"),
#     Input({"type": "main-stat", "index": MATCH}, "value"),
# )
# def validate_main_stat_wildcard(value):
#     """
#     Validate the player's main stat using the same approach as analysis.py,.

#     but with wildcard matching for multiple players/rows.
#     """
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_main_stat(
#         "main_stat",
#         stat_val,
#         lower=stat_ranges["main_stat"]["lower"],
#         upper=stat_ranges["main_stat"]["upper"],
#     )
#     return valid_stat_return if result else invalid_stat_return


# @app.callback(
#     Output({"type": "DET", "index": MATCH}, "valid"),
#     Output({"type": "DET", "index": MATCH}, "invalid"),
#     Input({"type": "DET", "index": MATCH}, "value"),
# )
# def validate_det_stat_wildcard(value):
#     """Validate the player's Determination stat using wildcard matching."""
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_meldable_stat(
#         "DET",
#         stat_val,
#         lower=stat_ranges["DET"]["lower"],
#         upper=stat_ranges["DET"]["upper"],
#     )
#     return valid_stat_return if result else invalid_stat_return


# @app.callback(
#     Output({"type": "speed-stat", "index": MATCH}, "valid"),
#     Output({"type": "speed-stat", "index": MATCH}, "invalid"),
#     Input({"type": "speed-stat", "index": MATCH}, "value"),
# )
# def validate_speed_stat_wildcard(value):
#     """Validate the player's Speed (SkS/SpS) stat using wildcard matching."""
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_speed_stat(stat_val)
#     if not result:
#         return invalid_stat_return
#     # Also ensure it fits the acceptable range from stat_ranges if desired
#     if (
#         stat_val < stat_ranges["SPEED"]["lower"]
#         or stat_val > stat_ranges["SPEED"]["upper"]
#     ):
#         return invalid_stat_return
#     return valid_stat_return


# @app.callback(
#     Output({"type": "CRT", "index": MATCH}, "valid"),
#     Output({"type": "CRT", "index": MATCH}, "invalid"),
#     Input({"type": "CRT", "index": MATCH}, "value"),
# )
# def validate_crit_stat_wildcard(value):
#     """Validate the player's Critical Hit stat using wildcard matching."""
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_meldable_stat(
#         "CRT",
#         stat_val,
#         lower=stat_ranges["CRT"]["lower"],
#         upper=stat_ranges["CRT"]["upper"],
#     )
#     return valid_stat_return if result else invalid_stat_return


# @app.callback(
#     Output({"type": "DH", "index": MATCH}, "valid"),
#     Output({"type": "DH", "index": MATCH}, "invalid"),
#     Input({"type": "DH", "index": MATCH}, "value"),
# )
# def validate_dh_stat_wildcard(value):
#     """Validate the player's Direct Hit stat using wildcard matching."""
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_meldable_stat(
#         "DH",
#         stat_val,
#         lower=stat_ranges["DH"]["lower"],
#         upper=stat_ranges["DH"]["upper"],
#     )
#     return valid_stat_return if result else invalid_stat_return


# @app.callback(
#     Output({"type": "WD", "index": MATCH}, "valid"),
#     Output({"type": "WD", "index": MATCH}, "invalid"),
#     Input({"type": "WD", "index": MATCH}, "value"),
# )
# def validate_wd_stat_wildcard(value):
#     """Validate the player's Weapon Damage stat using wildcard matching."""
#     if not value:
#         return invalid_stat_return
#     try:
#         stat_val = int(value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_weapon_damage(stat_val)
#     if not result:
#         return invalid_stat_return

#     if stat_val < stat_ranges["WD"]["lower"] or stat_val > stat_ranges["WD"]["upper"]:
#         return invalid_stat_return
#     return valid_stat_return


# @app.callback(
#     Output({"type": "TEN", "index": MATCH}, "valid"),
#     Output({"type": "TEN", "index": MATCH}, "invalid"),
#     Input({"type": "TEN", "index": MATCH}, "value"),
#     Input({"type": "main-stat-label", "index": MATCH}, "children"),
# )
# def validate_tenacity_wildcard(ten_value, main_stat_label):
#     """
#     Validate the player's Tenacity stat if they're a tank (main_stat_label == "STR"),.

#     otherwise always valid. No form feedback is returned.
#     """
#     # Non-tank => always valid
#     if main_stat_label != "STR:":
#         return valid_stat_return

#     # Tank => do normal validation
#     if not ten_value:
#         return invalid_stat_return
#     try:
#         stat_val = int(ten_value)
#     except ValueError:
#         return invalid_stat_return

#     result, _ = validate_meldable_stat(
#         "TEN",
#         stat_val,
#         lower=stat_ranges["TEN"]["lower"],
#         upper=stat_ranges["TEN"]["upper"],
#     )
#     return valid_stat_return if result else invalid_stat_return


# @callback(
#     Output("party-compute", "disabled"),
#     Output("party-compute", "children"),
#     Input({"type": "main-stat", "index": ALL}, "valid"),
#     Input({"type": "main-stat", "index": ALL}, "invalid"),
#     Input({"type": "TEN", "index": ALL}, "valid"),
#     Input({"type": "TEN", "index": ALL}, "invalid"),
#     Input({"type": "DET", "index": ALL}, "valid"),
#     Input({"type": "DET", "index": ALL}, "invalid"),
#     Input({"type": "speed-stat", "index": ALL}, "valid"),
#     Input({"type": "speed-stat", "index": ALL}, "invalid"),
#     Input({"type": "CRT", "index": ALL}, "valid"),
#     Input({"type": "CRT", "index": ALL}, "invalid"),
#     Input({"type": "DH", "index": ALL}, "valid"),
#     Input({"type": "DH", "index": ALL}, "invalid"),
#     Input({"type": "WD", "index": ALL}, "valid"),
#     Input({"type": "WD", "index": ALL}, "invalid"),
#     Input("party-compute", "children"),
# )
# def validate_job_builds(
#     main_stat_valid_list,
#     main_stat_invalid_list,
#     ten_valid_list,
#     ten_invalid_list,
#     det_valid_list,
#     det_invalid_list,
#     speed_valid_list,
#     speed_invalid_list,
#     crit_valid_list,
#     crit_invalid_list,
#     dh_valid_list,
#     dh_invalid_list,
#     wd_valid_list,
#     wd_invalid_list,
#     party_compute_button_text,
# ):
#     """
#     Hide the 'party-compute-div' if any required stats are invalid or if.

#     not all are valid. This replaces the previous check on job-build-input.
#     """
#     # If any stat input is invalid across all players, hide the compute button:
#     any_invalid = (
#         any(main_stat_invalid_list)
#         or any(ten_invalid_list)
#         or any(det_invalid_list)
#         or any(speed_invalid_list)
#         or any(crit_invalid_list)
#         or any(dh_invalid_list)
#         or any(wd_invalid_list)
#     )
#     # Or if not all are valid, also hide:
#     not_all_valid = not (
#         all(main_stat_valid_list)
#         and all(ten_valid_list)
#         and all(det_valid_list)
#         and all(speed_valid_list)
#         and all(crit_valid_list)
#         and all(dh_valid_list)
#         and all(wd_valid_list)
#     )

#     # If any stat is invalid or not all valid => disable button
#     disabled_compute_button = any_invalid or not_all_valid

#     append_text = " [invalid job build(s), check inputs]"
#     party_compute_button_text = party_compute_button_text.removesuffix(append_text)

#     if disabled_compute_button:
#         party_compute_button_text += append_text
#     return disabled_compute_button, party_compute_button_text


# def job_progress(job_list, active_job):
#     active_style = {
#         "font-family": "job-icons",
#         "font-size": "1.2em",
#         "position": "relative",
#         "top": "4px",
#         "font-weight": "500",
#         "color": "#009670",
#     }
#     inactive_style = {
#         "font-family": "job-icons",
#         "font-size": "1.2em",
#         "position": "relative",
#         "top": "4px",
#     }

#     current_job = [
#         html.Span([j, " "], style=inactive_style)
#         if j != active_job
#         else html.Span([j, " "], style=active_style)
#         for j in job_list
#     ]

#     return ["Analysis progress: "] + current_job


# @app.long_callback(
#     Output("url", "href", allow_duplicate=True),
#     Output("party-analysis-error", "children"),
#     Output("analysis-history", "data", allow_duplicate=True),
#     Input("party-compute", "n_clicks"),
#     State("party-phase-select", "value"),
#     State({"type": "job-name", "index": ALL}, "children"),
#     State({"type": "player-id", "index": ALL}, "children"),
#     State({"type": "main-stat", "index": ALL}, "value"),
#     State({"type": "TEN", "index": ALL}, "value"),
#     State({"type": "DET", "index": ALL}, "value"),
#     State({"type": "speed-stat", "index": ALL}, "value"),
#     State({"type": "CRT", "index": ALL}, "value"),
#     State({"type": "DH", "index": ALL}, "value"),
#     State({"type": "WD", "index": ALL}, "value"),
#     State({"type": "main-stat-label", "index": ALL}, "children"),
#     State({"type": "player-name", "index": ALL}, "children"),
#     State({"type": "job-build-input", "index": ALL}, "value"),
#     State("party-encounter-name", "children"),
#     State("fflogs-url2", "value"),
#     State("fflogs-party-encounter", "data"),
#     State("analysis-history", "data"),
#     running=[(Output("party-compute", "disabled"), True, False)],
#     progress=[
#         Output("party-progress", "value"),
#         Output("party-progress", "max"),
#         Output("party-progress-header", "children"),
#     ],
#     prevent_initial_call=True,
# )
# def analyze_party_rotation(
#     set_progress,
#     n_clicks,
#     fight_phase,
#     job,
#     player_id,
#     main_stat_no_buff,
#     secondary_stat_no_buff,
#     determination,
#     speed,
#     crit,
#     dh,
#     weapon_damage,
#     main_stat_label,
#     player_name,
#     job_build_url,
#     encounter_name,
#     fflogs_url,
#     fflogs_data,
#     analysis_history: list[dict],
# ):
#     """
#     Analyze and compute the damage distribution of a whole party.

#     This is done by
#     computing the damage distribution of each job and convolving each one together.

#     The likelihood of faster kill times is also analyzed, by computing the percentile
#     of the damage distribution >= Boss HP when the each job's rotation is shortened by
#     2.5, 5.0, 7.5, and 10.0 seconds.

#     Notation:

#     party rotation = (truncated party rotation) + (party rotation clipping)

#     party_{} -
#     {}_truncat
#     """
#     updated_url = dash.no_update
#     if n_clicks is None:
#         return updated_url, [], analysis_history

#     if isinstance(fight_phase, list):
#         fight_phase = fight_phase[0]
#     else:
#         fight_phase = int(fight_phase)

#     # TODO: get etro URL
#     set_progress((0, len(job), "Getting LB damage", "Analysis progress:"))

#     try:
#         report_id = fflogs_data["report_id"]
#         fight_id = fflogs_data["fight_id"]
#         error_message = ""
#     except Exception:
#         report_id, fight_id, error_message = parse_fflogs_url(fflogs_url)

#         if fight_id == "last":
#             fight_id, error_message = _query_last_fight_id(report_id)

#     if error_message != "":
#         return updated_url, [error_alert(error_message)], analysis_history

#     encounter_id, lb_player_id, pet_id_map = get_party_analysis_calculation_info(
#         report_id, fight_id
#     )

#     if encounter_id is None:
#         return (
#             updated_url,
#             [error_alert("Log URL changed, please resubmit.")],
#             analysis_history,
#         )

#     level = encounter_level[encounter_id]

#     # Get Limit Break instances
#     # Check if LB was used, get its ID if it was
#     if lb_player_id is not None:
#         lb_damage_events_df, error_message = limit_break_damage_events(
#             report_id, fight_id, lb_player_id, fight_phase
#         )
#         if error_message != "":
#             return updated_url, [error_alert(error_message)], analysis_history
#         lb_damage = lb_damage_events_df["amount"].sum()
#     else:
#         lb_damage_events_df = pd.DataFrame(columns=["timestamp"])
#         lb_damage = 0

#     # Party bonus to main stat
#     main_stat_multiplier = 1 + len(set(main_stat_label)) / 100

#     # Fixed time between phases, need to find killing damage event
#     find_t_clip_offset = False
#     perform_kill_time_analysis = True

#     if encounter_id in custom_t_clip_encounter_phases.keys():
#         if fight_phase in custom_t_clip_encounter_phases[encounter_id]:
#             find_t_clip_offset = True

#     if encounter_id in skip_kill_time_analysis_phases.keys():
#         if fight_phase in skip_kill_time_analysis_phases[encounter_id]:
#             perform_kill_time_analysis = False

#     t_clips = [2.5, 5, 7.5, 10]
#     t_clip_offset = 0
#     # Damage step size for
#     n_data_points = 5000

#     ######
#     # Player-level analyses
#     ######

#     prior_analysis_info = [
#         search_prior_player_analyses(
#             report_id,
#             fight_id,
#             fight_phase,
#             unabbreviated_job_map[job[a]],
#             player_name[a],
#             main_stat_no_buff[a],
#             secondary_stat_no_buff[a],
#             determination[a],
#             speed[a],
#             crit[a],
#             dh[a],
#             weapon_damage[a],
#             weapon_delays[job[a].upper()],
#         )
#         for a in range(len(job))
#     ]
#     player_analysis_ids = [p[0] for p in prior_analysis_info]
#     any_redo_flags = any([p[1] for p in prior_analysis_info])

#     if len(set(player_analysis_ids)) == 8:
#         party_analysis_id, redo_party_analysis_flag = (
#             check_prior_party_analysis_via_player_analyses(player_analysis_ids)
#         )
#     else:
#         party_analysis_id = None
#         redo_party_analysis_flag = 0

#     if (
#         (party_analysis_id is not None)
#         and (not any_redo_flags)
#         and (redo_party_analysis_flag == 0)
#     ):
#         return f"/party_analysis/{party_analysis_id}", [], analysis_history

#     # Compute player-level analyses
#     success, results = player_analysis_loop(
#         report_id,
#         fight_id,
#         encounter_name,
#         encounter_id,
#         player_name,
#         player_id,
#         fight_phase,
#         pet_id_map,
#         job,
#         set_progress,
#         main_stat_no_buff,
#         main_stat_multiplier,
#         secondary_stat_no_buff,
#         speed,
#         determination,
#         crit,
#         dh,
#         weapon_damage,
#         level,
#         job_build_url,
#         player_analysis_ids,
#         # t_clips,
#     )

#     if success:
#         (
#             job_rotation_analyses_list,
#             job_rotation_pdf_list,
#             job_db_rows,
#         ) = results

#     else:
#         error_message = results[-2]
#         insert_error_player_analysis(*results)
#         return updated_url, [error_alert(error_message)], analysis_history

#     if perform_kill_time_analysis:
#         if job_rotation_analyses_list[0].phase_information is not None:
#             # FIXME: surely I can do this less dumb
#             # P5 enrage requires offset to be found b/c of cutscene
#             furthest_phase = max(
#                 [i["id"] for i in job_rotation_analyses_list[0].phase_information]
#             )
#             if (
#                 (encounter_id == 1079)
#                 & ((fight_phase == 5) | ((fight_phase == 0) & (furthest_phase == 5)))
#                 & (not job_rotation_analyses_list[0].kill)
#             ):
#                 find_t_clip_offset = True

#             if find_t_clip_offset:
#                 t_clip_offset = calculate_time_clip_offset(job_rotation_analyses_list)

#         clipping_success, clipping_results = create_rotation_clippings(
#             report_id,
#             fight_id,
#             encounter_name,
#             encounter_id,
#             player_name,
#             player_id,
#             fight_phase,
#             job,
#             main_stat_no_buff,
#             main_stat_multiplier,
#             secondary_stat_no_buff,
#             speed,
#             determination,
#             crit,
#             dh,
#             weapon_damage,
#             level,
#             player_analysis_ids,
#             t_clips,
#             t_clip_offset,
#             job_rotation_analyses_list,
#         )

#         if clipping_success:
#             (
#                 job_rotation_clipping_pdf_list,
#                 job_rotation_clipping_analyses,
#             ) = clipping_results
#         else:
#             error_message = clipping_results[-2]
#             insert_error_player_analysis(*clipping_results)
#             return updated_url, [error_alert(error_message)], analysis_history
#     else:
#         job_rotation_clipping_pdf_list = [None] * len(job)
#         job_rotation_clipping_analyses = [None] * len(job)
#     ########################
#     # Party-level analysis
#     ########################
#     try:
#         party_rotation = party_analysis_portion(
#             job_rotation_analyses_list,
#             job_rotation_pdf_list,
#             job_rotation_clipping_analyses,
#             job_rotation_clipping_pdf_list,
#             lb_damage,
#             lb_damage_events_df,
#             party_analysis_id,
#             t_clips,
#             t_clip_offset,
#             perform_kill_time_analysis,
#             n_data_points,
#             level,
#         )

#     # FIXME: remove medication amt (-1)
#     except Exception as e:
#         party_error_info = (
#             report_id,
#             fight_id,
#             fight_phase,
#             encounter_id,
#             job,
#             player_name,
#             player_id,
#             main_stat_no_buff,
#             secondary_stat_no_buff,
#             determination,
#             speed,
#             crit,
#             dh,
#             weapon_damage,
#             main_stat_multiplier,
#             -1,
#             job_build_url,
#             str(e),
#             traceback.format_exc(),
#         )

#         insert_error_party_analysis(*party_error_info)
#         return updated_url, [error_alert(str(e))], analysis_history
#     ##########################################
#     # Export all the data we've generated
#     ##########################################

#     # Party analysis
#     # Create an ID if it's not a recompute
#     if party_analysis_id is None:
#         party_analysis_id = str(uuid4())

#     # Job analyses
#     creation_ts = datetime.now()
#     for a in range(len(job_rotation_pdf_list)):
#         # Write RotationTable
#         with open(
#             BLOB_URI / f"rotation-object-{player_analysis_ids[a]}.pkl", "wb"
#         ) as f:
#             pickle.dump(job_rotation_analyses_list[a], f)

#         # Convert job analysis to data class
#         job_analysis_data = job_analysis_to_data_class(
#             job_rotation_pdf_list[a], job_rotation_analyses_list[a].fight_dps_time
#         )

#         job_analysis_data.interpolate_distributions(
#             rotation_n=n_data_points, action_n=n_data_points
#         )

#         # Write data class
#         with open(
#             BLOB_URI / f"job-analysis-data-{player_analysis_ids[a]}.pkl", "wb"
#         ) as f:
#             pickle.dump(job_analysis_data, f)

#         # Update report table
#         unflag_redo_rotation(player_analysis_ids[a])
#         unflag_report_recompute(player_analysis_ids[a])
#         update_report_table(job_db_rows[a])
#         update_player_analysis_creation_table((player_analysis_ids[a], creation_ts))
#         pass

#     # Write party analysis to disk
#     with open(
#         BLOB_URI / "party-analyses" / f"party-analysis-{party_analysis_id}.pkl", "wb"
#     ) as f:
#         pickle.dump(party_rotation, f)

#     # Update party report table
#     individual_analysis_ids = [None] * 8
#     individual_analysis_ids[0 : len(player_analysis_ids)] = player_analysis_ids
#     db_row = tuple(
#         [
#             party_analysis_id,
#             report_id,
#             fight_id,
#             fight_phase,
#         ]
#         + individual_analysis_ids
#         + [0]
#     )
#     update_party_report_table(db_row)

#     log_datetime = datetime.fromtimestamp(
#         job_rotation_analyses_list[0].fight_start_time / 1000
#     )
#     party_history_record = serialize_analysis_history_record(
#         party_analysis_id,
#         "Party Analysis",
#         creation_ts,
#         log_datetime,
#         encounter_id,
#         fight_phase,
#         party_rotation.fight_duration,
#         "",
#         "",
#         float(party_rotation.percentile),
#         None,
#         None,
#     )

#     analysis_history = upsert_local_store_record(
#         analysis_history, party_history_record, preserve_analysis_datetime=True
#     )
#     current_job = "Analysis progress: Done!"
#     set_progress((a + 1, len(job), current_job, "Analysis progress:"))
#     updated_url = f"/party_analysis/{party_analysis_id}"
#     return updated_url, [], analysis_history


# def player_analysis_loop(
#     report_id: str,
#     fight_id: int,
#     encounter_name: str,
#     encounter_id: int,
#     player_name: List[str],
#     player_id: List[int],
#     fight_phase: int,
#     pet_id_map: Dict[int, Any],
#     job: List[str],
#     set_progress: Any,
#     main_stat_no_buff: List[float],
#     main_stat_multiplier: float,
#     secondary_stat_no_buff: List[Union[float, str]],
#     speed: List[int],
#     determination: List[int],
#     crit: List[int],
#     dh: List[int],
#     weapon_damage: List[int],
#     level: int,
#     job_build_url: List[str],
#     player_analysis_ids: List[Optional[str]],
# ) -> Tuple[
#     bool,
#     Union[
#         Tuple[
#             List[Any],
#             List[Any],
#             List[Any],
#             Dict[float, List[Any]],
#             Dict[float, List[Any]],
#         ],
#         Tuple[Any, ...],
#     ],
# ]:
#     """
#     Analyzes each player's combat performance by building rotation analyses and PDFs.

#     This function:
#       1. Retrieves or creates a unique analysis ID for each player.
#       2. Builds a rotation analysis DataFrame and PDF for each job in the fight.
#       3. Saves the rotation data and associated PDFs into lists and dictionaries
#          for future reference.
#       4. Catches exceptions to gather and return error information if the analysis fails.

#     Args:
#         report_id (str): FFLogs report identifier.
#         fight_id (int): Numeric identifier for the fight.
#         encounter_name (str): Name of the encounter.
#         encounter_id (int): Numeric ID of the encounter.
#         player_name (List[str]): List of player names.
#         player_id (List[int]): List of player IDs.
#         fight_phase (int): Current phase in the fight.
#         pet_id_map (Dict[int, Any]): Maps player IDs to pet data.
#         job (List[str]): List of job abbreviations (e.g. ["DRG", "WHM"]).
#         set_progress (Any): Callback to update or display progress.
#         main_stat_no_buff (List[float]): Main stat values before buffs for each player.
#         main_stat_multiplier (float): Multiplier applied to main stat.
#         secondary_stat_no_buff (List[Union[float, str]]): Secondary stat values before buffs.
#         speed (List[int]): Speed values for each player's job.
#         determination (List[int]): Determination values for each player's job.
#         crit (List[int]): Critical hit rate values for each player's job.
#         dh (List[int]): Direct hit rate values for each player's job.
#         weapon_damage (List[int]): Weapon damage values for each player's job.
#         medication_amt (int): Amount of medicine/food buffs applied.
#         level (int): Character level used in calculations.
#         job_build_url (List[str]): Gearset URLs for each player.
#         player_analysis_ids (List[Optional[str]]): List of existing or None player analysis IDs.
#         t_clips (List[float]): List of time clipping points for truncated analyses.

#     Returns:
#         Tuple[bool, Union[
#             Tuple[
#                 List[Any],  # job_rotation_analyses_list
#                 List[Any],  # job_rotation_pdf_list
#                 List[Any],  # job_db_rows
#                 Dict[float, List[Any]],  # job_rotation_clipping_pdf_list
#                 Dict[float, List[Any]]   # job_rotation_clipping_analyses
#             ],
#             Tuple[Any, ...]  # player_error_info if an exception occurs
#         ]]:
#         A two-element tuple indicating success (True/False) and either:
#          - On success (True), a tuple of lists/dicts containing rotation analyses and PDFs.
#          - On failure (False), a tuple of error information.
#     """
#     rotation_dmg_step = LEVEL_STEP_MAP[level]["rotation_dmg_step"]
#     action_delta = LEVEL_STEP_MAP[level]["action_delta"]
#     rotation_delta = LEVEL_STEP_MAP[level]["rotation_delta"]

#     # Whole job rotations
#     job_rotation_analyses_list = []
#     job_rotation_pdf_list = []
#     job_db_rows = []

#     try:
#         a = 0
#         for a in range(len(job)):
#             full_job = reverse_abbreviated_role_map[job[a]]
#             role = role_mapping[full_job]
#             delay = weapon_delays[job[a].upper()]

#             # Progress bar
#             current_job = job_progress(job, job[a])
#             set_progress((a, len(job), current_job))

#             main_stat_buff = int(main_stat_no_buff[a] * main_stat_multiplier)
#             # Assign analysis ID
#             # only append if analysis ID is None so the ID isn't overwritten
#             if player_analysis_ids[a] is None:
#                 player_analysis_ids[a] = str(uuid4())
#             main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"]

#             secondary_stat_type = role_stat_dict[role]["secondary_stat"]["placeholder"]
#             secondary_stat_buff = (
#                 int(caster_healer_strength[job[a].upper()] * main_stat_multiplier)
#                 if role in ("Healer", "Magical Ranged")
#                 else secondary_stat_no_buff[a]
#             )
#             secondary_stat_buff = (
#                 None if secondary_stat_buff == "None" else secondary_stat_buff
#             )
#             job_build_id, build_provider = parse_build_uuid(job_build_url[a], 0)

#             job_rotation_analyses_list.append(
#                 RotationTable(
#                     headers,
#                     report_id,
#                     fight_id,
#                     full_job,
#                     player_id[a],
#                     crit[a],
#                     dh[a],
#                     determination[a],
#                     main_stat_no_buff[a],
#                     weapon_damage[a],
#                     level,
#                     fight_phase,
#                     damage_buff_table,
#                     critical_hit_rate_table,
#                     direct_hit_rate_table,
#                     guaranteed_hits_by_action_table,
#                     guaranteed_hits_by_buff_table,
#                     potency_table,
#                     encounter_phases=encounter_phases,
#                     pet_ids=pet_id_map[player_id[a]],
#                     tenacity=secondary_stat_buff,
#                 )
#             )

#             job_rotation_pdf_list.append(
#                 rotation_analysis(
#                     role,
#                     full_job,
#                     job_rotation_analyses_list[a].rotation_df,
#                     1,
#                     main_stat_buff,
#                     secondary_stat_buff,
#                     determination[a],
#                     speed[a],
#                     crit[a],
#                     dh[a],
#                     weapon_damage[a],
#                     delay,
#                     main_stat_no_buff[a],
#                     rotation_step=rotation_dmg_step,
#                     rotation_delta=rotation_delta,
#                     action_delta=action_delta,
#                     compute_mgf=False,
#                     level=level,
#                 )
#             )

#             # Collect DB rows to insert at the end
#             # FIXME: remove medication amt (-1)
#             job_db_rows.append(
#                 (
#                     player_analysis_ids[a],
#                     report_id,
#                     fight_id,
#                     fight_phase,
#                     encounter_name,
#                     job_rotation_analyses_list[a].fight_dps_time,
#                     full_job,
#                     player_name[a],
#                     int(main_stat_no_buff[a]),
#                     int(main_stat_buff),
#                     main_stat_type,
#                     None
#                     if secondary_stat_no_buff[a] == "None"
#                     else secondary_stat_no_buff[a],
#                     secondary_stat_buff,
#                     secondary_stat_type,
#                     int(determination[a]),
#                     int(speed[a]),
#                     int(crit[a]),
#                     int(dh[a]),
#                     int(weapon_damage[a]),
#                     delay,
#                     -1,
#                     main_stat_multiplier,
#                     job_build_id,
#                     build_provider,
#                     0,
#                     0,
#                 )
#             )

#             # FIXME: should probably move to option in the class
#             actions_df = job_rotation_analyses_list[a].actions_df
#             if role in ("Healer", "Magical Ranged"):
#                 actions_df = actions_df[actions_df["ability_name"] != "attack"]

#         success = True
#         return (
#             success,
#             (
#                 job_rotation_analyses_list,
#                 job_rotation_pdf_list,
#                 job_db_rows,
#             ),
#         )

#     # FIXME: remove medication amt (-1)
#     except Exception as e:
#         success = False
#         player_error_info = (
#             report_id,
#             fight_id,
#             player_id[a],
#             encounter_id,
#             encounter_name,
#             fight_phase,
#             full_job,
#             player_name[a],
#             int(main_stat_no_buff[a]),
#             int(main_stat_buff),
#             main_stat_type,
#             None if secondary_stat_no_buff[a] == "None" else secondary_stat_no_buff[a],
#             secondary_stat_buff,
#             secondary_stat_type,
#             int(determination[a]),
#             int(speed[a]),
#             int(crit[a]),
#             int(dh[a]),
#             int(weapon_damage[a]),
#             delay,
#             -1,
#             main_stat_multiplier,
#             str(e),
#             traceback.format_exc(),
#         )
#         return success, (player_error_info)


# def create_rotation_clippings(
#     report_id: str,
#     fight_id: int,
#     encounter_name: str,
#     encounter_id: int,
#     player_name: List[str],
#     player_id: List[int],
#     fight_phase: int,
#     job: List[str],
#     main_stat_no_buff: List[float],
#     main_stat_multiplier: float,
#     secondary_stat_no_buff: List[Union[float, str]],
#     speed: List[int],
#     determination: List[int],
#     crit: List[int],
#     dh: List[int],
#     weapon_damage: List[int],
#     level: int,
#     player_analysis_ids: List[Optional[str]],
#     t_clips: List[float],
#     t_clip_offset: float,
#     job_rotation_analyses_list,
# ):
#     rotation_dmg_step = LEVEL_STEP_MAP[level]["rotation_dmg_step"]
#     action_delta = LEVEL_STEP_MAP[level]["action_delta"]
#     rotation_delta = LEVEL_STEP_MAP[level]["rotation_delta"]
#     try:
#         # Job rotation clippings to unconvolve out later
#         job_rotation_clipping_pdf_list = {t: [] for t in t_clips}
#         job_rotation_clipping_analyses = {t: [] for t in t_clips}
#         for a in range(len(job)):
#             clipped_rotations = []

#             full_job = reverse_abbreviated_role_map[job[a]]
#             role = role_mapping[full_job]
#             delay = weapon_delays[job[a].upper()]
#             main_stat_buff = int(main_stat_no_buff[a] * main_stat_multiplier)
#             # Assign analysis ID
#             # only append if analysis ID is None so the ID isn't overwritten
#             if player_analysis_ids[a] is None:
#                 player_analysis_ids[a] = str(uuid4())
#             main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"]

#             secondary_stat_type = role_stat_dict[role]["secondary_stat"]["placeholder"]
#             secondary_stat_buff = (
#                 int(caster_healer_strength[job[a].upper()] * main_stat_multiplier)
#                 if role in ("Healer", "Magical Ranged")
#                 else secondary_stat_no_buff[a]
#             )
#             secondary_stat_buff = (
#                 None if secondary_stat_buff == "None" else secondary_stat_buff
#             )

#             for idx, t in enumerate(t_clips):
#                 # t += t_clip_offset
#                 # print(t)
#                 # FIXME: can remove
#                 actions_df = job_rotation_analyses_list[a].actions_df
#                 if role in ("Healer", "Magical Ranged"):
#                     actions_df = actions_df[actions_df["ability_name"] != "attack"]

#                 clipped_rotations.append(
#                     job_rotation_analyses_list[a].make_rotation_df(
#                         actions_df,
#                         t_end_clip=t + t_clip_offset,
#                         return_clipped=True,
#                     )
#                 )
#                 if clipped_rotations[idx] is not None:
#                     # Compute mean via MGFs because it is cheap to compute
#                     # and will be exact. We need the mean later when we unconvolve
#                     # to create a truncated rotation.
#                     job_rotation_clipping_analyses[t].append(
#                         rotation_analysis(
#                             role,
#                             full_job,
#                             clipped_rotations[idx],
#                             1,
#                             main_stat_buff,
#                             secondary_stat_buff,
#                             determination[a],
#                             speed[a],
#                             crit[a],
#                             dh[a],
#                             weapon_damage[a],
#                             delay,
#                             main_stat_no_buff[a],
#                             rotation_step=rotation_dmg_step,
#                             rotation_delta=rotation_delta,
#                             action_delta=action_delta,
#                             compute_mgf=True,
#                             # test_error_log=True
#                         )
#                     )
#                     job_rotation_clipping_pdf_list[t].append(
#                         job_rotation_clipping_analyses[t][-1]
#                     )
#         success = True
#         return (
#             success,
#             (
#                 job_rotation_clipping_pdf_list,
#                 job_rotation_clipping_analyses,
#             ),
#         )

#     except Exception as e:
#         success = False
#         # FIXME: remove medication amt (-1)
#         player_error_info = (
#             report_id,
#             fight_id,
#             player_id[a],
#             encounter_id,
#             encounter_name,
#             fight_phase,
#             full_job,
#             player_name[a],
#             int(main_stat_no_buff[a]),
#             int(main_stat_buff),
#             main_stat_type,
#             None if secondary_stat_no_buff[a] == "None" else secondary_stat_no_buff[a],
#             secondary_stat_buff,
#             secondary_stat_type,
#             int(determination[a]),
#             int(speed[a]),
#             int(crit[a]),
#             int(dh[a]),
#             int(weapon_damage[a]),
#             delay,
#             -1,
#             main_stat_multiplier,
#             str(e),
#             traceback.format_exc(),
#         )
#         return success, (player_error_info)
#     pass


# def party_analysis_portion(
#     job_rotation_analyses_list: List[Any],
#     job_rotation_pdf_list: List[Any],
#     job_rotation_clipping_analyses: Dict[float, List[Any]],
#     job_rotation_clipping_pdf_list: Dict[float, List[Any]],
#     lb_damage: float,
#     lb_damage_events_df: pd.DataFrame,
#     party_analysis_id: Optional[str],
#     t_clips: List[float],
#     t_clip_offset: float,
#     perform_kill_time_analysis: bool,
#     n_data_points: int,
#     level: int,
# ) -> "PartyRotation":
#     """Perform party-level analysis by combining individual rotation analyses.

#     Takes individual player rotation analyses and combines them into a party-level
#     analysis. Computes overall party damage distributions, statistics, and creates
#     truncated analyses for different kill times.

#     Args:
#         job_rotation_analyses_list: List of rotation analyses for each player
#         job_rotation_pdf_list: List of probability distributions for each rotation
#         job_rotation_clipping_analyses: Dictionary mapping clip times to truncated analyses
#         job_rotation_clipping_pdf_list: Dictionary mapping clip times to truncated PDFs
#         lb_damage: Total damage from limit breaks
#         lb_damage_events_df: DataFrame containing limit break damage events
#         party_analysis_id: Unique ID for this party analysis, generated if None
#         t_clips: List of times to analyze truncated rotations
#         n_data_points: Number of points to use when interpolating distributions
#         level: Character level used for damage step calculations

#     Returns:
#         PartyRotation: Object containing party-level damage distributions and statistics
#     """
#     rotation_dmg_step = LEVEL_STEP_MAP[level]["rotation_dmg_step"]

#     rotation_pdf, rotation_supp = rotation_dps_pdf(job_rotation_pdf_list, lb_damage)

#     if perform_kill_time_analysis:
#         truncated_party_distribution, party_distribution_clipping = kill_time_analysis(
#             job_rotation_analyses_list,
#             job_rotation_pdf_list,
#             lb_damage_events_df,
#             job_rotation_clipping_analyses,
#             job_rotation_clipping_pdf_list,
#             rotation_pdf,
#             rotation_supp,
#             t_clips,
#             rotation_dmg_step,
#         )
#     else:
#         truncated_party_distribution = {
#             t: {"pdf": [1, 0], "support": [1, 0]} for t in t_clips
#         }
#         party_distribution_clipping = {
#             t: {"pdf": [1, 0], "support": [1, 0]} for t in t_clips
#         }
#     #
#     boss_total_hp = (
#         sum([a.actions_df["amount"].sum() for a in job_rotation_analyses_list])
#         + lb_damage
#     )

#     party_mean = sum([a.rotation_mean for a in job_rotation_pdf_list])
#     party_std = sum([a.rotation_variance for a in job_rotation_pdf_list]) ** (0.5)
#     party_skewness = sum(
#         [
#             a.rotation_skewness * a.rotation_variance ** (3 / 2)
#             for a in job_rotation_pdf_list
#         ]
#     ) / sum([a.rotation_variance ** (3 / 2) for a in job_rotation_pdf_list])

#     # FIXME: have fight/phase duration
#     # and active dps time
#     active_dps_time = job_rotation_analyses_list[0].fight_dps_time

#     if job_rotation_analyses_list[0].phase > 0:
#         fight_duration = (
#             job_rotation_analyses_list[0].phase_end_time
#             - job_rotation_analyses_list[0].phase_start_time
#         ) / 1000
#     else:
#         fight_duration = (
#             job_rotation_analyses_list[0].fight_end_time
#             - job_rotation_analyses_list[0].fight_start_time
#         ) / 1000

#     party_rotation = PartyRotation(
#         party_analysis_id,
#         boss_total_hp,
#         active_dps_time,
#         fight_duration,
#         perform_kill_time_analysis,
#         lb_damage_events_df,
#         party_mean,
#         party_std,
#         party_skewness,
#         rotation_pdf,
#         rotation_supp,
#         [
#             SplitPartyRotation(
#                 t,
#                 t_clip_offset,
#                 boss_total_hp,
#                 truncated_party_distribution[t]["pdf"],
#                 truncated_party_distribution[t]["support"],
#                 party_distribution_clipping[t]["pdf"],
#                 party_distribution_clipping[t]["support"],
#             )
#             for t in t_clips
#         ],
#     )
#     # Interpolate onto n_data_points
#     party_rotation.interpolate_distributions(
#         rotation_n=n_data_points, split_n=n_data_points
#     )

#     return party_rotation


# def calculate_time_clip_offset(job_rotation_analyses_list: List[Any]) -> float:
#     """
#     Calculate the time clip offset to account for downtime phases in combat analysis.

#     Phases in combat often include significant downtime where no actions occur,
#     which can skew the time clipping (`t_clip`) calculations. This function
#     identifies the end of active combat by locating the timestamp of the final
#     action performed by any player and computes the offset needed to adjust
#     the clipping time accordingly.

#     Args:
#         job_rotation_analyses_list (List[Any]):
#             A list of job rotation analysis objects. Each object is expected to have
#             an `actions_df` attribute, which is a pandas DataFrame containing
#             a `'timestamp'` column, and a `fight_end_time` attribute representing
#             the end time of the fight in milliseconds.

#     Returns:
#         float:
#             The computed time clip offset in seconds. This offset adjusts for
#             the downtime by calculating the difference between the fight's end
#             time and the timestamp of the last action, then converting it from
#             milliseconds to seconds.
#     """
#     final_action_time = max(
#         [t.actions_df["timestamp"].iloc[-1] for t in job_rotation_analyses_list]
#     )
#     t_clip_offset = (
#         float(job_rotation_analyses_list[0].fight_end_time - final_action_time) / 1000
#     )
#     return t_clip_offset
