# fmt: off
import sys
# I hate pythonpath i hate pythonpath i hate pythonpath i hate pythonpath
sys.path.append("../../") 
# fmt: on

import datetime
import pickle
from uuid import uuid4

import dash
import dash_bootstrap_components as dbc
from api_queries import (
    get_encounter_job_info,
    headers,
    parse_etro_url,
    parse_fflogs_url,
)
from cards import (
    initialize_action_card,
    initialize_fflogs_card,
    initialize_job_build,
    initialize_new_action_card,
    initialize_results,
    initialize_rotation_card,
)
from config import BLOB_URI, DEBUG, DRY_RUN
from dash import Input, Output, Patch, State, callback, dcc, html
from dash.exceptions import PreventUpdate
from dmg_distribution import (
    get_dps_dmg_percentile,
    job_analysis_to_data_class,
)
from figures import (
    make_action_box_and_whisker_figure,
    make_action_pdfs_figure,
    make_rotation_pdf_figure,
    make_rotation_percentile_table,
)
from job_data.job_data import weapon_delays
from job_data.job_warnings import job_warnings
from job_data.roles import abbreviated_job_map, role_stat_dict
from job_data.valid_encounters import patch_times, valid_encounters
from shared_elements import (
    etro_build,
    format_kill_time_str,
    read_encounter_table,
    read_report_table,
    rotation_analysis,
    set_secondary_stats,
    unflag_redo_rotation,
    unflag_report_recompute,
    update_access_table,
    update_encounter_table,
    update_report_table,
)

from crit_app.job_data.valid_encounters import encounter_level
from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable


def page_title(analysis_id=None):
    if analysis_id is None:
        return ""
    encounter_info = read_encounter_table()
    report = read_report_table()
    fight_data = (
        report[report["analysis_id"] == analysis_id]
        .merge(
            encounter_info[["report_id", "fight_id", "kill_time"]],
            on=["report_id", "fight_id"],
            how="inner",
        )
        .iloc[0]
    )

    return "Analysis: {} ({}); {} ({})".format(
        fight_data.player_name,
        abbreviated_job_map[fight_data.job].upper(),
        fight_data.encounter_name,
        format_kill_time_str(fight_data.kill_time),
    )


def metas(analysis_id=None):
    if analysis_id is not None:
        encounter_info = read_encounter_table()
        report = read_report_table()
        fight_data = (
            report[report["analysis_id"] == analysis_id]
            .merge(
                encounter_info[["report_id", "fight_id", "kill_time"]],
                on=["report_id", "fight_id"],
                how="inner",
            )
            .iloc[0]
        )
        app_description = "View analysis for {} ({}) on {} ({})".format(
            fight_data.player_name,
            abbreviated_job_map[fight_data.job].upper(),
            fight_data.encounter_name,
            format_kill_time_str(fight_data.kill_time),
        )
    else:
        app_description = "Analyze crit RNG for FFXIV!"
    app_image = "crit_app/assets/meta_image.png"
    page_title = "Player analysis"

    return [
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"property": "twitter:card", "content": "summary_large_image"},
        {"property": "twitter:url", "content": "https://www.wealthdashboard.app/"},
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
    path="/",
    name=page_title,
    meta_tags=metas,
)


### Helper functions ###


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


def ad_hoc_job_invalid(job: str, log_time: int):
    """Collection of various conditions to make certain jobs un-analyzable.
    For example, 7.0 - 7.01 Monk's job gauge is not modeled, so it cannot be analyzed.

    These *should* be fairly rare.

    Args:
        job (str): Job name, FFLogs case style
        time (int): Start time of the log, to determine patch number.
    """

    if (
        (job == "Monk")
        & (log_time > patch_times[7.0]["start"])
        & (log_time < patch_times[7.0]["end"])
    ):
        return True
    else:
        return False


def show_job_options(job_information, role, start_time):
    """
    Show which jobs are available to analyze with radio buttons.
    """
    tank_radio_items = []
    healer_radio_items = []
    melee_radio_items = []
    physical_ranged_radio_items = []
    magical_ranged_radio_items = []

    for d in job_information:
        invalid = ad_hoc_job_invalid(d["job"], start_time)
        label_text = html.P(
            [
                html.Span(
                    [abbreviated_job_map[d["job"]]],
                    style={
                        "font-family": "job-icons",
                        "font-size": "1.4em",
                        "position": "relative",
                        "top": "4px",
                    },
                ),
                f" {d['player_name']}",
                " [Unsupported]" if invalid else "",
            ],
            style={"position": "relative", "bottom": "9px"},
        )
        if d["role"] == "Tank":
            tank_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Tank" != role) or invalid,
                }
            )
        elif d["role"] == "Healer":
            healer_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Healer" != role) or invalid,
                }
            )
        elif d["role"] == "Melee":
            melee_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Melee" != role) or invalid,
                }
            )
        elif d["role"] == "Physical Ranged":
            physical_ranged_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Physical Ranged" != role) or invalid,
                }
            )
        elif d["role"] == "Magical Ranged":
            magical_ranged_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": ("Magical Ranged" != role) or invalid,
                }
            )

    return (
        tank_radio_items,
        healer_radio_items,
        melee_radio_items,
        physical_ranged_radio_items,
        magical_ranged_radio_items,
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
        report_df = report_df[report_df["analysis_id"] == analysis_id]

        # Message to display if something goes wrong.
        error_children = [
            html.H2("404 Not Found"),
            html.P(
                [
                    "The link entered does not exist. ",
                    html.A("Click here", href="/"),
                    " to return home and analyze a rotation.",
                ]
            ),
        ]

        # redirect to 404 if no analysis page exists
        if len(report_df) == 0:
            return html.Div(error_children)
        else:
            # Read in encounter info
            encounter_df = read_encounter_table()

            # Merge to get all relevant info
            analysis_details = (
                report_df.merge(
                    encounter_df.drop(
                        columns=["encounter_id", "encounter_name", "job"]
                    ),
                    how="inner",
                    on=["report_id", "fight_id", "player_name"],
                )
                .iloc[0]
                .fillna("")
            )

            # Filter down encounter DF to relevant information
            encounter_df = encounter_df[
                (encounter_df["fight_id"] == analysis_details["fight_id"])
                & (encounter_df["report_id"] == analysis_details["report_id"])
                & (encounter_df["role"] != "Limit Break")
            ]
            #### Job build / Etro card setup ####
            if (analysis_details["etro_id"] is not None) and (
                analysis_details["etro_id"] != ""
            ):
                etro_url = f"https://etro.gg/gearset/{analysis_details['etro_id']}"
            else:
                etro_url = None

            #### FFLogs Card Info ####
            # FFlogs URL
            report_id = analysis_details["report_id"]
            fight_id = analysis_details["fight_id"]
            fflogs_url = f"https://www.fflogs.com/reports/{report_id}#fight={fight_id}"

            # Encounter Info
            boss_name = analysis_details["encounter_name"]
            fight_duration = format_kill_time_str(analysis_details["kill_time"])
            encounter_info = f"{boss_name} ({fight_duration})"
            # Job selection info

            # Player information
            # There's a 50% chance the wrong character will be reported
            # if you have two characters with the same name on the same job
            character = analysis_details["player_name"]
            player_id = analysis_details["player_id"]
            role = analysis_details["role"]
            encounter_id = encounter_df["encounter_id"].iloc[0]
            level = encounter_level[encounter_id]

            redo_rotation = analysis_details["redo_rotation_flag"]
            recompute_pdf_flag = analysis_details["redo_dps_pdf_flag"]
            # recompute_flag = 1

            # Player stat info
            main_stat = int(analysis_details["main_stat"])
            main_stat_pre_bonus = analysis_details["main_stat_pre_bonus"]
            if analysis_details["secondary_stat_pre_bonus"] != "":
                secondary_stat_pre_bonus = int(
                    float(analysis_details["secondary_stat_pre_bonus"])
                )
            else:
                secondary_stat_pre_bonus = ""

            if analysis_details["secondary_stat"] != "":
                secondary_stat = int(float(analysis_details["secondary_stat"]))
            else:
                secondary_stat = ""
            determination = analysis_details["determination"]
            speed_stat = analysis_details["speed"]
            crit = analysis_details["critical_hit"]
            direct_hit = analysis_details["direct_hit"]
            weapon_damage = analysis_details["weapon_damage"]
            delay = analysis_details["delay"]

            party_bonus = analysis_details["party_bonus"]
            medication_amt = analysis_details["medication_amount"]
            player_job_no_space = analysis_details["job"]
            player_id = int(analysis_details["player_id"])
            pet_ids = analysis_details["pet_ids"]

            # Get actions and create a rotation again, used if the RotationTable class updates.
            if redo_rotation:
                rotation_object = RotationTable(
                    headers,
                    analysis_details["report_id"],
                    int(analysis_details["fight_id"]),
                    player_job_no_space,
                    player_id,
                    crit,
                    direct_hit,
                    determination,
                    medication_amt,
                    level,
                    damage_buff_table,
                    critical_hit_rate_table,
                    direct_hit_rate_table,
                    guaranteed_hits_by_action_table,
                    guaranteed_hits_by_buff_table,
                    potency_table,
                    pet_ids,
                )

                action_df = rotation_object.actions_df
                rotation_df = rotation_object.rotation_df

                with open(BLOB_URI / f"rotation-object-{analysis_id}.pkl", "wb") as f:
                    pickle.dump(rotation_object, f)

                unflag_redo_rotation(analysis_id)
            else:
                try:
                    with open(
                        BLOB_URI / f"rotation-object-{analysis_id}.pkl", "rb"
                    ) as outp:
                        rotation_object = pickle.load(outp)
                    action_df = rotation_object.actions_df
                    rotation_df = rotation_object.rotation_df

                except Exception as e:
                    error_children.append(
                        html.P(f"The following error was encountered: {str(e)}")
                    )
                    return html.Div(error_children)

            # Recompute DPS distributions if flagged to do so.
            # Happens if `ffxiv_stats` updates with some sort of correction.
            if recompute_pdf_flag:
                job_analysis_object = rotation_analysis(
                    role,
                    player_job_no_space,
                    rotation_df,
                    rotation_object.fight_time,
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
                encounter_df.to_dict("records"), role, rotation_object.fight_start_time
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
                etro_url,
                role,
                main_stat_pre_bonus,
                secondary_stat_pre_bonus,
                determination,
                speed_stat,
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
                    job_build,
                    html.Br(),
                    fflogs_card,
                    html.Br(),
                    result_card,
                ]
            )


@callback(
    Output("action-pdf-fig", "figure"),
    Input("action-dropdown", "value"),
    State("action-pdf-fig", "figure"),
)
def select_actions(actions, action_graph):
    actions_actual_dps = [a + " (Actual DPS)" for a in actions]
    patched_action_figure = Patch()
    new_data = action_graph["data"]

    for n in new_data:
        if (n["name"] in actions) or (n["name"] in actions_actual_dps):
            n["visible"] = True
        else:
            n["visible"] = False

    patched_action_figure["data"] = new_data
    return patched_action_figure


@callback(
    Output("action-dropdown", "value"),
    State("action-dropdown", "options"),
    Input("action-reset", "n_clicks"),
)
def reset_action_filters(action_list, n):
    return action_list


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
def fill_role_stat_labels(role):
    if role == "Unsupported":
        raise PreventUpdate

    return (
        role_stat_dict[role]["main_stat"]["label"],
        role_stat_dict[role]["main_stat"]["placeholder"],
        role_stat_dict[role]["speed_stat"]["label"],
        role_stat_dict[role]["speed_stat"]["placeholder"],
    )


@callback(
    Output("etro-url-feedback", "children"),
    Output("etro-url", "valid"),
    Output("etro-url", "invalid"),
    Output("etro-build-name-div", "children"),
    Output("role-select", "value"),
    Output("main-stat", "value"),
    Output("TEN", "value"),
    Output("DET", "value"),
    Output("speed-stat", "value"),
    Output("CRT", "value"),
    Output("DH", "value"),
    Output("WD", "value"),
    # Output("DEL", "value"),
    Output("party-bonus-warning", "children"),
    Input("etro-url-button", "n_clicks"),
    State("etro-url", "value"),
    State("role-select", "value"),
    prevent_initial_call=True,
)
def process_etro_url(n_clicks, url, default_role):
    """
    Get the report/fight ID from an fflogs URL, then determine the encounter ID, start time, and jobs present.
    """

    if n_clicks is None:
        raise PreventUpdate

    feedback = []
    invalid_return = [
        False,
        True,
        [],
        default_role,
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        # [],
        [],
    ]

    gearset_id, error_code = parse_etro_url(url)

    if error_code == 0:
        pass

    elif error_code == 1:
        feedback = ["This isn't an etro.gg link..."]
        return tuple(feedback + invalid_return)

    else:
        feedback = [
            "This doesn't appear to be a valid gearset. Please double check the link."
        ]
        return tuple(feedback + invalid_return)

    # Get the build if everything checks out
    (
        etro_call_successful,
        etro_error,
        build_name,
        build_role,
        primary_stat,
        tenacity,
        determination,
        speed,
        ch,
        dh,
        wd,
        delay,
        etro_party_bonus,
    ) = etro_build(gearset_id)

    if not etro_call_successful:
        return tuple([etro_error] + invalid_return)
    # job_abbreviated = build_result["jobAbbrev"]
    build_children = [html.H4(f"Build name: {build_name}")]

    if etro_party_bonus > 1.0:
        bonus_fmt = etro_party_bonus - 1
        warning_row = dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                f"Warning! The linked etro build has already applied a {bonus_fmt:.0%} bonus to its main stats. Values shown here have the party bonus removed..",
            ],
            color="warning",
            className="d-flex align-items-center",
        )
        primary_stat = int(primary_stat / etro_party_bonus)
    else:
        warning_row = []
    return (
        [],
        True,
        False,
        build_children,
        build_role,
        primary_stat,
        tenacity,
        determination,
        speed,
        ch,
        dh,
        wd,
        # delay,
        warning_row,
    )


@callback(
    Output("fflogs-card", "hidden"),
    Input("main-stat", "value"),
    Input("TEN", "value"),
    Input("DET", "value"),
    Input("speed-stat", "value"),
    Input("CRT", "value"),
    Input("DH", "value"),
    Input("WD", "value"),
    Input("role-select", "value"),
    Input("results-div", "hidden"),
)
def job_build_defined(
    main_stat,
    tenacity,
    determination,
    speed,
    crit,
    direct_hit,
    weapon_damage,
    role,
    results_hidden,
):
    """
    Check if any job build elements are missing, hide everything else if they are.
    """
    if (role == "Tank") & (tenacity is None):
        tenacity_missing = True

    else:
        tenacity_missing = False

    # TODO: will need to handle None secondary stat for roles without them.
    job_build_missing = (
        any(
            (elem is None) or (elem == [])
            for elem in [
                main_stat,
                determination,
                speed,
                crit,
                direct_hit,
                weapon_damage,
            ]
        )
        | tenacity_missing
    )
    return job_build_missing


@callback(
    Output("speed-stat", "valid"),
    Output("speed-stat", "invalid"),
    Input("speed-stat", "value"),
)
def validate_sps(spell_speed):
    if (spell_speed == []) or (spell_speed is None) or (spell_speed > 3):
        return True, False
    else:
        return False, True


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
    Output("encounter-info", "hidden"),
    Input("fflogs-url-state", "n_clicks"),
    State("fflogs-url", "value"),
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
    error_return = [
        [],
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
    ]

    report_id, fight_id, error_code = parse_fflogs_url(url)
    if error_code == 1:
        return tuple(["This link isn't FFLogs..."] + error_return)
    if error_code == 2:
        feedback_text = """Please enter a log linked to a specific kill.\nfight=last in the URL is also currently unsupported."""
        return tuple([feedback_text] + error_return)
    if error_code == 3:
        feedback_text = "Invalid report ID."
        return tuple([feedback_text] + error_return)

    (
        encounter_id,
        start_time,
        job_information,
        limit_break_information,
        kill_time,
        encounter_name,
        start_time,
        r,
    ) = get_encounter_job_info(report_id, int(fight_id))

    print(kill_time)
    fight_time_str = format_kill_time_str(kill_time)

    if encounter_id not in valid_encounters:
        feedback_text = f"Sorry, {encounter_name} is not supported."
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
            encounter_name,
            kill_time,
            k["player_name"],
            k["player_server"],
            k["player_id"],
            k["pet_ids"],
            k["job"],
            k["role"],
        )
        for k in job_information
    ]
    if not DRY_RUN:
        update_encounter_table(db_rows)

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
        False,
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
    healers,
    tanks,
    melees,
    phys_ranged,
    magic_ranged,
    healer_value,
    tank_value,
    melee_value,
    phys_ranged_value,
    magic_ranged_value,
):
    """
    Display button to compute DPS distributions once a job is selected. Otherwise, no button is shown.
    """
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
    if job_list is None or (selected_job == []) or (job_list == []):
        raise PreventUpdate

    # Get just the job names
    job_list = [x["value"] for x in job_list]
    selected_job = selected_job[0]
    if selected_job not in job_list:
        hide_button = True
        return hide_button
    else:
        hide_button = False
        return hide_button


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
    if (n_clicks is None) or DEBUG:
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
    # State("DEL", "value"),
    State("tincture-grade", "value"),
    State("fflogs-url", "value"),
    State("etro-url", "value"),
    Input("healer-jobs", "value"),
    Input("tank-jobs", "value"),
    Input("melee-jobs", "value"),
    Input("physical-ranged-jobs", "value"),
    Input("magical-ranged-jobs", "value"),
    prevent_initial_call=True,
)
def analyze_and_register_rotation(
    n_clicks,
    main_stat_pre_bonus,
    tenacity,
    determination,
    speed_stat,
    ch,
    dh,
    wd,
    # delay,
    medication_amt,
    fflogs_url,
    etro_url,
    healer_jobs=None,
    tank_jobs=None,
    melee_jobs=None,
    phys_ranged_jobs=None,
    magical_jobs=None,
):
    updated_url = dash.no_update

    job_player = [healer_jobs, tank_jobs, melee_jobs, phys_ranged_jobs, magical_jobs]

    if n_clicks is None:
        raise PreventUpdate

    job_player = [x for x in job_player if x is not None][0]
    report_id, fight_id, _ = parse_fflogs_url(fflogs_url)
    encounter_df = read_encounter_table()
    encounter_comparison_columns = ["report_id", "fight_id", "player_id"]

    player_info = encounter_df.loc[
        (
            encounter_df[encounter_comparison_columns]
            == (report_id, fight_id, job_player)
        ).all(axis=1)
    ].iloc[0]

    player = player_info["player_name"]
    job_no_space = player_info["job"]
    role = player_info["role"]
    encounter_id = player_info["encounter_id"]
    level = encounter_level[encounter_id]

    # Higher level = bigger damage = bigger discretization step size
    delta_map = {90: 4, 100: 9}

    main_stat_multiplier = (
        1 + len(set(encounter_df[encounter_df["role"] != "Limit Break"]["role"])) / 100
    )
    main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"].lower()
    main_stat = int(main_stat_pre_bonus * main_stat_multiplier)

    secondary_stat_type, secondary_stat_pre_bonus, secondary_stat = set_secondary_stats(
        role, abbreviated_job_map[job_no_space].upper(), main_stat_multiplier, tenacity
    )

    delay = weapon_delays[abbreviated_job_map[job_no_space].upper()]

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
            main_stat,
            secondary_stat,
            determination,
            speed_stat,
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

        if len(prior_analysis) >= 1:
            # redirect instead
            analysis_id = prior_analysis["analysis_id"].iloc[0]
            updated_url = f"/analysis/{analysis_id}"
            return (
                updated_url,
                ["Analyze rotation"],
                False,
                [],
                False,
            )

        if len(prior_analysis) == 0:
            pet_ids = player_info["pet_ids"]
            rotation = RotationTable(
                headers,
                report_id,
                fight_id,
                job_no_space,
                int(player_info["player_id"]),
                ch,
                dh,
                determination,
                medication_amt,
                level,
                damage_buff_table,
                critical_hit_rate_table,
                direct_hit_rate_table,
                guaranteed_hits_by_action_table,
                guaranteed_hits_by_buff_table,
                potency_table,
                pet_ids,
            )

            rotation_df = rotation.rotation_df
            t = rotation.fight_time
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

                db_row = (
                    analysis_id,
                    report_id,
                    fight_id,
                    encounter_name,
                    t,
                    job_no_space,
                    player,
                    int(main_stat_pre_bonus),
                    int(main_stat),
                    main_stat_type,
                    None
                    if role in ("Melee", "Physical Ranged")
                    else int(secondary_stat_pre_bonus),
                    None
                    if role in ("Melee", "Physical Ranged")
                    else int(secondary_stat),
                    secondary_stat_type,
                    int(determination),
                    int(speed_stat),
                    int(ch),
                    int(dh),
                    int(wd),
                    delay,
                    medication_amt,
                    main_stat_multiplier,
                    gearset_id,
                    redo_dps_pdf_flag,
                    redo_rotation_flag,
                )
                update_report_table(db_row)

            del job_analysis_object

    # Catch any error and display it, then reset the button/prompt
    except Exception as e:
        info = (
            report_id,
            fight_id,
            encounter_id,
            job_no_space,
            player,
            int(main_stat_pre_bonus),
            int(main_stat),
            main_stat_type,
            None
            if role in ("Melee", "Physical Ranged")
            else int(secondary_stat_pre_bonus),
            None if role in ("Melee", "Physical Ranged") else int(secondary_stat),
            secondary_stat_type,
            int(determination),
            int(speed_stat),
            int(ch),
            int(dh),
            int(wd),
            delay,
            medication_amt,
            main_stat_multiplier,
        )

        error_information = {"inputted_info": info, "exception": e}

        with open(
            BLOB_URI / "error-logs" / f"{datetime.datetime.now()}-error.pkl", "wb"
        ) as f:
            pickle.dump(error_information, f)

        return (
            updated_url,
            ["Analyze rotation"],
            False,
            [
                dbc.Alert(
                    [
                        html.P(
                            "Oops, the following error was encountered while creating and analyzing your rotation:"
                        ),
                        str(e),
                        html.P(
                            "This error has been logged and will be fixed when possible. No further action is required."
                        ),
                    ],
                    color="danger",
                )
            ],
            False,
        )
    updated_url = f"/analysis/{analysis_id}"
    return (updated_url, ["Analyze rotation"], False, [], False)
