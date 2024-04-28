import sqlite3
import datetime
import pickle
from uuid import uuid4
from ast import literal_eval

from ffxiv_stats.jobs import Healer, Tank, MagicalRanged, Melee, PhysicalRanged

import dash
from dash import Input, Output, State, dcc, html, callback, Patch
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import coreapi
import pandas as pd

from dmg_distribution import get_dps_dmg_percentile
from rotation import RotationTable
from job_data.job_data import weapon_delays
from job_data.data import (
    damage_buff_table,
    critical_hit_rate_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)

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
    headers,
)
from cards import (
    initialize_job_build,
    initialize_fflogs_card,
    initialize_rotation_card,
    initialize_action_card,
    initialize_results,
)
from job_data.job_warnings import job_warnings
from job_data.roles import role_stat_dict
from config import DB_URI, BLOB_URI, ETRO_TOKEN, DRY_RUN, DEBUG


dash.register_page(
    __name__,
    path_template="/analysis/<analysis_id>",
    path="/",
)


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
    player_df["pet_ids"] = player_df["pet_ids"].apply(
        lambda x: literal_eval(x) if x is not None else x
    )
    return player_df


def update_report_table(db_row):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    cur.execute(
        """
    insert into report 
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        db_row,
    )
    con.commit()
    cur.close()
    con.close()
    pass


def unflag_report_recompute(analysis_id):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(f"""
    update report set redo_dps_pdf_flag = 0 where analysis_id = "{analysis_id}"
    """)
    con.commit()
    cur.close()
    con.close()
    pass

def unflag_redo_rotation(analysis_id):
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()

    cur.execute(f"""
    update report set redo_rotation_flag = 0 where analysis_id = "{analysis_id}"
    """)
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
    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        db_rows,
    )
    # Drop any duplicate records
    cur.execute(
        """
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


def rotation_analysis(
    role: str,
    job_no_space: str,
    rotation_df,
    t: float,
    main_stat: int,
    secondary_stat: int,
    determination: int,
    speed_stat: int,
    ch: int,
    dh: int,
    wd: int,
    delay: float,
    main_stat_pre_bonus: int,
):
    """Analyze the rotation of a job.

    Args:
        role (str): Job role, Healer, Tank, Magical Ranged, Melee, or Physical Ranged
        job_no_space (str): Pascal case job, e.g., "WhiteMage"
        rotation_df (pandas DataFrame): rotation DataFrame
        t (float): Active fight time used to compute DPS
        main_stat (int): Amount of main stat.
        secondary_stat (int): Amount of secondary stat
        determination (int): Amount of determination stat.
        speed_stat (int): Amount of Skill/Spell Speed stat.
        ch (int): Amount of critical hit stat.
        dh (int): Amount of direct hit rate stat.
        wd (int): Amount of weapon damage stat.
        delay (float): Amount of weapon delay stat.
        main_stat_pre_bonus (int): Amount of main stat before n% party bonus, for pet attack power.

    Returns:
        ffxiv_stats job object: Object with analyzed rotation and DPS distributions.
    """

    if role == "Healer":
        job_obj = Healer(
            mind=main_stat,
            strength=secondary_stat,
            det=determination,
            spell_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
        )

    elif role == "Tank":
        job_obj = Tank(
            strength=main_stat,
            det=determination,
            skill_speed=speed_stat,
            tenacity=secondary_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            job=job_no_space,
            pet_attack_power=main_stat_pre_bonus,
            level=90,
        )

    elif role == "Magical Ranged":
        job_obj = MagicalRanged(
            intelligence=main_stat,
            strength=secondary_stat,
            det=determination,
            spell_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
        )

    elif role == "Melee":
        job_obj = Melee(
            main_stat=main_stat,
            det=determination,
            skill_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            job=job_no_space,
            pet_attack_power=main_stat_pre_bonus,
            level=90,
        )

    elif role == "Physical Ranged":
        job_obj = PhysicalRanged(
            dexterity=main_stat,
            det=determination,
            skill_speed=speed_stat,
            crit_stat=ch,
            dh_stat=dh,
            weapon_damage=wd,
            delay=delay,
            pet_attack_power=main_stat_pre_bonus,
            level=90,
        )
    else:
        raise ValueError("Incorrect role specified.")

    job_obj.attach_rotation(rotation_df, t)
    job_obj.action_moments = [None] * len(job_obj.action_moments)

    return job_obj


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
            analysis_details = report_df.merge(
                encounter_df.drop(columns=["encounter_id", "encounter_name", "job"]),
                how="inner",
                on=["report_id", "fight_id", "player_name"],
            ).iloc[0]

            # Filter down encounter DF to relevant information
            encounter_df = encounter_df[
                (encounter_df["fight_id"] == analysis_details["fight_id"])
                & (encounter_df["report_id"] == analysis_details["report_id"])
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
            fight_duration = analysis_details["kill_time"]
            fight_duration = (
                f"{int(fight_duration // 60)}:{int(fight_duration % 60):02d}"
            )
            encounter_info = f"{boss_name} ({fight_duration})"

            # add space to job name
            encounter_df["job"] = (
                encounter_df["job"]
                .str.replace(r"(\w)([A-Z])", r"\1 \2", regex=True)
                .str.strip()
            )

            # Job selection info

            # Player information
            # There's a 50% chance the wrong character will be reported
            # if you have two characters with the same name on the same job
            character = analysis_details["player_name"]
            player_id = analysis_details["player_id"]
            role = analysis_details["role"]

            job_radio_options = show_job_options(encounter_df.to_dict("records"), role)
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

            redo_rotation = analysis_details["redo_rotation_flag"]
            recompute_pdf_flag = analysis_details["redo_dps_pdf_flag"]
            # recompute_flag = 1

            #### Damage Distributions ####
            # Load in action_df and rotation object to display results
            try:
                action_df = pd.read_parquet(
                    BLOB_URI / f"action-df-{analysis_id}.parquet"
                )
                with open(BLOB_URI / f"rotation-obj-{analysis_id}.pkl", "rb") as outp:
                    job_object = pickle.load(outp)
            except Exception as e:
                error_children.append(
                    html.P(f"The following error was encountered: {str(e)}")
                )
                return html.Div(error_children)

            # Player stat info
            main_stat_pre_bonus = analysis_details["main_stat_pre_bonus"]
            secondary_stat_pre_bonus = (
                analysis_details["secondary_stat_pre_bonus"]
                if analysis_details["secondary_stat_pre_bonus"] is not None
                else ""
            )
            determination = job_object.det
            speed_stat = job_object.dot_speed_stat
            crit = job_object.crit_stat
            direct_hit = job_object.dh_stat
            weapon_damage = job_object.weapon_damage
            delay = job_object.delay

            party_bonus = analysis_details["party_bonus"]
            medication_amt = analysis_details["medication_amount"]
            player_job_no_space = analysis_details["job"]
            pet_ids = analysis_details["pet_ids"]

            # Get actions and create a rotation again, used if the RotationTable class updates.
            if redo_rotation:
                rotation = RotationTable(
                    headers,
                    report_id,
                    int(fight_id),
                    player_job_no_space,
                    int(player_id),
                    crit,
                    direct_hit,
                    determination,
                    medication_amt,
                    damage_buff_table,
                    critical_hit_rate_table,
                    direct_hit_rate_table,
                    guaranteed_hits_by_action_table,
                    guaranteed_hits_by_buff_table,
                    potency_table,
                    pet_ids,
                )
                actions_df = rotation.actions_df
                rotation_df = rotation.rotation_df

                actions_df.to_parquet(BLOB_URI / f"action-df-{analysis_id}.parquet")
                rotation_df.to_parquet(BLOB_URI / f"rotation-df-{analysis_id}.parquet")

                unflag_redo_rotation(analysis_id)
            else:
                rotation_df = job_object.rotation_df

            # Recompute DPS distributions if flagged to do so.
            # Happens if `ffxiv_stats` updates with some sort of correction.
            if recompute_pdf_flag:
                job_object = rotation_analysis(
                    role,
                    player_job_no_space,
                    rotation_df,
                    job_object.t,
                    analysis_details["main_stat"],
                    analysis_details["secondary_stat"],
                    determination,
                    speed_stat,
                    crit,
                    direct_hit,
                    weapon_damage,
                    delay,
                    main_stat_pre_bonus,
                )

                with open(BLOB_URI / f"rotation-obj-{analysis_id}.pkl", "wb") as outp:
                    pickle.dump(job_object, outp, pickle.HIGHEST_PROTOCOL)
                unflag_report_recompute(analysis_id)
            # DPS of each action + the entire rotation

            action_dps = (
                action_df[["ability_name", "amount"]].groupby("ability_name").sum()
                / job_object.t
            ).reset_index()
            rotation_dps = action_dps["amount"].sum()
            rotation_percentile = (
                get_dps_dmg_percentile(
                    rotation_dps,
                    job_object.rotation_dps_distribution,
                    job_object.rotation_dps_support,
                )
                / 100
            )

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

            action_options = action_dps["ability_name"].tolist()
            action_values = action_dps["ability_name"].tolist()

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
            action_card = initialize_action_card(
                action_graph, action_summary_table, action_options, action_values
            )
            result_card = initialize_results(
                character,
                crit_text,
                alert_child,
                rotation_card,
                action_card,
                analysis_url,
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
    patched_action_figure = Patch()
    new_data = action_graph["data"]

    for n in new_data:
        if n["name"] in actions:
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
    Output("main-stat-label", "children"),
    Output("main-stat", "placeholder"),
    Output("secondary-stat-label", "children"),
    Output("secondary-stat", "placeholder"),
    Output("secondary-stat", "disabled"),
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
        role_stat_dict[role]["secondary_stat"]["label"],
        role_stat_dict[role]["secondary_stat"]["placeholder"],
        True if role in ("Melee", "Physical Ranged") else False,
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
    Output("secondary-stat", "value"),
    Output("DET", "value"),
    Output("speed-stat", "value"),
    Output("CRT", "value"),
    Output("DH", "value"),
    Output("WD", "value"),
    Output("DEL", "value"),
    Output("party-bonus-warning", "children"),
    Output("main-stat-slider", "value"),
    Input("etro-url-button", "n_clicks"),
    State("main-stat-slider", "value"),
    State("etro-url", "value"),
    State("role-select", "value"),
    prevent_initial_call=True,
)
def process_etro_url(n_clicks, party_bonus, url, default_role):
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
            default_role,
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
            default_role,
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

    if job_abbreviated in ("WHM", "AST", "SGE", "SCH"):
        build_role = "Healer"
        main_stat_str = "MND"
        secondary_stat_str = "STR"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("WAR", "PLD", "DRK", "GNB"):
        build_role = "Tank"
        main_stat_str = "STR"
        secondary_stat_str = "TEN"
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BLM", "SMN", "RDM"):
        build_role = "Magical Ranged"
        main_stat_str = "INT"
        secondary_stat_str = "STR"
        speed_stat_str = "SPS"
    elif job_abbreviated in ("MNK", "DRG", "SAM", "RPR", "NIN"):
        build_role = "Melee"
        main_stat_str = "STR" if job_abbreviated != "NIN" else "DEX"
        secondary_stat_str = None
        speed_stat_str = "SKS"
    elif job_abbreviated in ("BRD", "DNC", "MCH"):
        build_role = "Physical Ranged"
        main_stat_str = "DEX"
        secondary_stat_str = None
        speed_stat_str = "SKS"

    else:
        build_role = "Unsupported"

    if build_role == "Unsupported":
        feedback = f"{job_abbreviated} is currently not supported."
        return (
            feedback,
            False,
            True,
            [],
            build_role,
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

    primary_stat = total_params[main_stat_str]["value"]
    dh = total_params["DH"]["value"]
    ch = total_params["CRT"]["value"]
    determination = total_params["DET"]["value"]
    speed = total_params[speed_stat_str]["value"]
    wd = total_params["Weapon Damage"]["value"]
    etro_party_bonus = build_result["partyBonus"]

    if build_role in ("Healer", "Magical Ranged"):
        if job_abbreviated == "SCH":
            secondary_stat = 350
        elif job_abbreviated == "WHM":
            secondary_stat = 214
        elif job_abbreviated == "SGE":
            secondary_stat = 233
        elif job_abbreviated == "AST":
            secondary_stat = 194
        elif job_abbreviated == "RDM":
            secondary_stat = 226
        elif job_abbreviated == "SMN":
            secondary_stat = 370
        else:
            secondary_stat = 194

    elif build_role == "Tank":
        secondary_stat = total_params[secondary_stat_str]["value"]

    else:
        secondary_stat = "None"

    # Weapon delay is read differently for normal weapons and relics
    # If normal weapon if the weapon key exists
    if build_result["weapon"] is not None:
        weapon_id = build_result["weapon"]
        weapon_action = ["equipment", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["delay"] / 1000

    # Relic weapon if the relic key exists
    elif build_result["relics"] is not None:
        weapon_id = build_result["relics"]["weapon"]
        weapon_action = ["relic", "read"]
        weapon_params = {"id": weapon_id}
        weapon_result = client.action(schema, weapon_action, params=weapon_params)
        delay = weapon_result["baseItem"]["delay"] / 1000

    # Fall back to hard-coded values by job if something goes wrong
    else:
        delay = weapon_delays[job_abbreviated]

    print(primary_stat, dh, ch, determination, speed, wd, delay, etro_party_bonus)

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
            build_role,
            primary_stat,
            secondary_stat,
            determination,
            speed,
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
        build_role,
        primary_stat,
        secondary_stat,
        determination,
        speed,
        ch,
        dh,
        wd,
        delay,
        [],
        party_bonus,
    )


@callback(
    Output("fflogs-card", "hidden"),
    Input("main-stat", "value"),
    Input("secondary-stat", "value"),
    Input("DET", "value"),
    Input("speed-stat", "value"),
    Input("CRT", "value"),
    Input("DH", "value"),
    Input("WD", "value"),
    Input("DEL", "value"),
    Input("results-div", "hidden"),
)
def job_build_defined(
    main_stat,
    secondary_stat,
    determination,
    speed,
    crit,
    direct_hit,
    weapon_damage,
    delay,
    results_hidden,
):
    """
    Check if any job build elements are missing, hide everything else if they are.
    """
    # TODO: will need to handle None secondary stat for roles without them.
    job_build_missing = any(
        (elem is None) or (elem == [])
        for elem in [
            main_stat,
            secondary_stat,
            determination,
            speed,
            crit,
            direct_hit,
            weapon_damage,
            delay,
        ]
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


@callback(Output("DEL", "valid"), Output("DEL", "invalid"), Input("DEL", "value"))
def validate_del(delay):
    if (delay == []) or (delay is None) or (delay <= 4):
        return True, False
    else:
        return False, True


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
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": "Melee" != role,
                }
            )
        elif d["role"] == "Physical Ranged":
            physical_ranged_radio_items.append(
                {
                    "label": label_text,
                    "value": d["player_id"],
                    "disabled": "Physical Ranged" != role,
                }
            )
        elif d["role"] == "Magical Ranged":
            magical_ranged_radio_items.append(
                {
                    "label": label_text,
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

    report_id, fight_id, error_code = parse_fflogs_url(url)
    if error_code == 1:
        return (
            "This link isn't FFLogs...",
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
        )

    if error_code == 2:
        feedback_text = """Please enter a log linked to a specific kill.\nfight=last in the URL is also currently unsupported."""
        return (
            feedback_text,
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
        )
    if error_code == 3:
        feedback_text = "Invalid report ID."
        return (
            feedback_text,
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
        )

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

    if encounter_id not in [1069, 1070, 88, 89, 90, 91, 92]:
        feedback_text = "Sorry, only fights from Anabeiseos are currently supported."
        return (
            feedback_text,
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
        )

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
    # print(encounter_id, start_time, job_information)

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
    Output("url", "href"),
    Output("compute-dmg-button", "children", allow_duplicate=True),
    Output("compute-dmg-button", "disabled", allow_duplicate=True),
    Output("crit-result-text", "children"),
    Input("compute-dmg-button", "n_clicks"),
    State("main-stat", "value"),
    State("secondary-stat", "value"),
    State("DET", "value"),
    State("speed-stat", "value"),
    State("CRT", "value"),
    State("DH", "value"),
    State("WD", "value"),
    State("DEL", "value"),
    State("main-stat-slider", "value"),
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
    secondary_stat_pre_bonus,
    determination,
    speed_stat,
    ch,
    dh,
    wd,
    delay,
    main_stat_multiplier,
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
        # return updated_url, ["Analyze rotation"], False, True, [], [], [], [], []

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
    main_stat_type = role_stat_dict[role]["main_stat"]["placeholder"].lower()
    secondary_stat_type = (
        None
        if role in ("Melee", "Physical Ranged")
        else role_stat_dict[role]["secondary_stat"]["placeholder"].lower()
    )

    main_stat = int(main_stat_pre_bonus * main_stat_multiplier)

    secondary_stat = (
        None if role in ("Melee", "Physical Ranged") else int(secondary_stat_pre_bonus)
    )
    if secondary_stat_type in (
        "mind",
        "strength",
        "dexterity",
        "intelligence",
        "vitality",
    ):
        secondary_stat = int(secondary_stat * main_stat_multiplier)

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
                damage_buff_table,
                critical_hit_rate_table,
                direct_hit_rate_table,
                guaranteed_hits_by_action_table,
                guaranteed_hits_by_buff_table,
                potency_table,
                pet_ids,
            )

            action_df = rotation.actions_df
            rotation_df = rotation.rotation_df
            t = rotation.fight_time
            encounter_name = rotation.fight_name

            job_obj = rotation_analysis(
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
            )

            analysis_id = str(uuid4())
            redo_rotation_flag = 0
            redo_dps_pdf_flag = 0

            if not DRY_RUN:
                action_df.to_parquet(BLOB_URI / f"action-df-{analysis_id}.parquet")
                rotation_df.to_parquet(BLOB_URI / f"rotation-df-{analysis_id}.parquet")
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
