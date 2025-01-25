import sqlite3

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import ALL, Input, Output, State, callback, dcc, html

from crit_app.config import DB_URI
from crit_app.job_data.encounter_data import encounter_information
from crit_app.job_data.roles import abbreviated_job_map

dash.register_page(
    __name__,
    path="/errors",
)

encounter_df = pd.DataFrame(encounter_information)


def build_table(dataframe: pd.DataFrame):
    if dataframe.empty:
        return dbc.Alert("No errors found.", color="info")

    # Define columns in the order you want to display them:
    columns = [
        "error_id",
        "error_ts",  # We'll convert this to a YYYY-MM-DD date
        "fflogs_url",
        "encounter_name",
        "phase",
        "player_name",
        "job",
        "main_stat",
        "secondary_stat",
        "determination",
        "speed",
        "critical_hit",
        "direct_hit",
        "weapon_damage",
        "scope",
        "error_message",
        "traceback",
    ]
    # Define corresponding headers:
    headers = [
        "ID",
        "Date",
        "Report",
        "Encounter",
        "Phase",
        "Player",
        "Job",
        "Main Stat",
        "SEC",
        "DET",
        "SPD",
        "CRT",
        "DHR",
        "WD",
        "Scope",
        "Error",
        "Traceback",
    ]

    # Add "Resolved" column
    columns.append("error_active")
    headers.append("Resolved")

    table_header = [html.Thead(html.Tr([html.Th(h) for h in headers]))]

    table_body_rows = []
    for _, row in dataframe.iterrows():
        cells = []
        for col in columns:
            if col == "error_ts":
                # Format the date as YYYY-MM-DD
                parsed_date = ""
                if pd.notnull(row[col]):
                    parsed_date = pd.to_datetime(row[col]).strftime("%Y-%m-%d")
                cells.append(html.Td(parsed_date))

            elif col == "fflogs_url":
                link = html.A("View FFLogs", href=row[col], target="_blank")
                cells.append(html.Td(link))

            elif col == "error_active":
                # Show 1 = active, 0 = resolved
                checked = row[col] == 0
                # Include scope in ID, so we know which table to update
                cells.append(
                    html.Td(
                        dbc.Checklist(
                            options=[{"label": "", "value": "resolved"}],
                            value=["resolved"] if checked else [],
                            inline=True,
                            id={
                                "type": "resolve-check",
                                "error_id": row["error_id"],
                                "scope": row["scope"],  # "Player" or "Party"
                            },
                        )
                    )
                )

            elif col == "traceback":
                traceback_str = str(row[col]) if pd.notnull(row[col]) else ""
                cells.append(
                    html.Td(
                        html.Pre(
                            traceback_str,
                            style={"whiteSpace": "pre-wrap", "width": "425px"},
                        ),
                        style={"width": "425px"},
                    )
                )

            else:
                cells.append(html.Td(str(row[col]) if pd.notnull(row[col]) else ""))

        table_body_rows.append(html.Tr(cells))

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)


def layout():
    """
    Layout for the error dashboard.

    Provides:
      - A button to push/pull data from the database.
      - Two tables displaying active and resolved errors.
      - A bar chart showing error counts by error_week.
    """
    return dbc.Container(
        [
            # Row with both buttons side by side
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Pull Errors", id="refresh-button", color="primary"
                            ),
                            dbc.Button(
                                "Push Resolved Errors",
                                id="push-resolved-button",
                                color="success",
                                className="ms-2",
                            ),
                        ]
                    )
                ]
            ),
            html.Br(),
            dbc.Row([dbc.Col(dcc.Graph(id="error-run-chart"), width=12)]),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Active Errors"),
                            html.Div(id="active-errors-table"),
                        ],
                        md=6,
                    ),
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Resolved Errors"),
                            html.Div(id="resolved-errors-table"),
                        ],
                        md=6,
                    ),
                ]
            ),
        ],
        fluid=True,
        style={"maxWidth": "100%"},  # Ensures full-width container
    )


@callback(
    Output("active-errors-table", "children"),
    Output("resolved-errors-table", "children"),
    Output("error-run-chart", "figure"),
    Input("refresh-button", "n_clicks"),
    prevent_initial_call=True,
)
def show_errors(n_clicks):
    """
    Query the database for errors and split them into active (error_active=1).

    and resolved (error_active=0). Also generate a run chart by error_week.
    """
    # Pull from DB
    query = """
    SELECT
        error_id,
        "https://www.fflogs.com/reports/" || report_id || "?fight=" || fight_id || "&type=damage-done" AS fflogs_url,
        encounter_id,
        COALESCE(phase_id,fight_phase) AS phase,  
        player_name,
        job,
        COALESCE(main_stat_pre_bonus, main_stat_no_buff) AS main_stat,
        COALESCE(secondary_stat, secondary_stat_no_buff) AS secondary_stat,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        scope,
        traceback,
        error_message,
        error_ts,
        DATE(
            error_ts,
            '-' || ((CAST(strftime('%w', error_ts) AS INTEGER) + 6) % 7) || ' days'
        ) AS error_week,
        error_active
    FROM (
        SELECT
            error_id,
            report_id,
            fight_id,
            phase_id,
            player_name,
            job,
            main_stat_pre_bonus,
            secondary_stat,
            determination,
            speed,
            critical_hit,
            direct_hit,
            weapon_damage,
            'Player' AS scope,
            traceback,
            error_message,
            error_ts,
            error_active,
            NULL AS fight_phase,
            NULL AS main_stat_no_buff,
            NULL AS secondary_stat_no_buff,
            encounter_id
        FROM error_player_analysis
        UNION
        SELECT
            error_id,
            report_id,
            fight_id,
            NULL AS phase_id,
            player_name,
            job,
            NULL AS main_stat_pre_bonus,
            NULL AS secondary_stat,
            determination,
            speed,
            critical_hit,
            direct_hit,
            weapon_damage,
            'Party' AS scope,
            traceback,
            error_message,
            error_ts,
            error_active,
            fight_phase,
            main_stat_no_buff,
            secondary_stat_no_buff,
            encounter_id
        FROM error_party_analysis
    )
    ORDER BY error_ts DESC;
    """
    con = sqlite3.connect(DB_URI)
    df = pd.read_sql_query(query, con)
    df = df.merge(
        encounter_df[["encounter_id", "encounter_name"]], how="left", on="encounter_id"
    )
    df["job"] = df["job"].replace(abbreviated_job_map).str.upper()
    con.close()

    # Separate active vs resolved
    active_df = df[df["error_active"] == 1].copy()
    resolved_df = df[df["error_active"] == 0].copy()

    # Build run chart counts
    weekly_counts = (
        df.groupby("error_week")
        .size()
        .reset_index(name="Count")
        .sort_values("error_week")
    )
    fig = px.bar(
        weekly_counts,
        x="error_week",
        y="Count",
        title="Weekly Error Counts",
        template="plotly_dark",
    )

    return build_table(active_df), build_table(resolved_df), fig


@callback(
    Output("active-errors-table", "children", allow_duplicate=True),
    Output("resolved-errors-table", "children", allow_duplicate=True),
    Output("error-run-chart", "figure", allow_duplicate=True),
    Input("push-resolved-button", "n_clicks"),
    State({"type": "resolve-check", "error_id": ALL, "scope": ALL}, "value"),
    State({"type": "resolve-check", "error_id": ALL, "scope": ALL}, "id"),
    prevent_initial_call=True,
)
def push_resolved_errors(n_clicks, all_values, all_ids):
    """
    When "Push Resolved Errors" is clicked, update error_active=0 for checked items,.

    or =1 for unchecked items, across both player and party tables,
    determined by 'scope' in the ID.
    Then refresh the tables and chart.
    """
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    # Update DB for each checkbox
    con = sqlite3.connect(DB_URI)
    cur = con.cursor()
    for checkbox_value, checkbox_id in zip(all_values, all_ids):
        is_resolved = "resolved" in checkbox_value
        new_status = 0 if is_resolved else 1
        error_id = checkbox_id["error_id"]
        scope = checkbox_id["scope"]  # "Player" or "Party"

        if scope == "Player":
            update_sql = """
                UPDATE error_player_analysis
                SET error_active = ?
                WHERE error_id = ?
            """
        else:  # scope == "Party"
            update_sql = """
                UPDATE error_party_analysis
                SET error_active = ?
                WHERE error_id = ?
            """

        cur.execute(update_sql, (new_status, error_id))

    con.commit()
    cur.close()
    con.close()

    # After updating, re-run the same logic as show_errors() to get fresh data
    query = """
    SELECT
        error_id,
        "https://www.fflogs.com/reports/" || report_id || "?fight=" || fight_id || "&type=damage-done" AS fflogs_url,
        encounter_id,
        COALESCE(phase_id,fight_phase) AS phase,  
        player_name,
        job,
        COALESCE(main_stat_pre_bonus, main_stat_no_buff) AS main_stat,
        COALESCE(secondary_stat, secondary_stat_no_buff) AS secondary_stat,
        determination,
        speed,
        critical_hit,
        direct_hit,
        weapon_damage,
        scope,
        traceback,
        error_message,
        error_ts,
        DATE(
            error_ts,
            '-' || ((CAST(strftime('%w', error_ts) AS INTEGER) + 6) % 7) || ' days'
        ) AS error_week,
        error_active
    FROM (
        SELECT
            error_id,
            report_id,
            fight_id,
            phase_id,
            player_name,
            job,
            main_stat_pre_bonus,
            secondary_stat,
            determination,
            speed,
            critical_hit,
            direct_hit,
            weapon_damage,
            'Player' AS scope,
            traceback,
            error_message,
            error_ts,
            error_active,
            NULL AS fight_phase,
            NULL AS main_stat_no_buff,
            NULL AS secondary_stat_no_buff,
            encounter_id
        FROM error_player_analysis
        UNION
        SELECT
            error_id,
            report_id,
            fight_id,
            NULL AS phase_id,
            player_name,
            job,
            NULL AS main_stat_pre_bonus,
            NULL AS secondary_stat,
            determination,
            speed,
            critical_hit,
            direct_hit,
            weapon_damage,
            'Party' AS scope,
            traceback,
            error_message,
            error_ts,
            error_active,
            fight_phase,
            main_stat_no_buff,
            secondary_stat_no_buff,
            encounter_id
        FROM error_party_analysis
    )
    ORDER BY error_ts DESC;
    """
    con = sqlite3.connect(DB_URI)
    refreshed_df = pd.read_sql_query(query, con)
    con.close()

    # Merge encounter info again if needed...
    refreshed_df = refreshed_df.merge(
        encounter_df[["encounter_id", "encounter_name"]], how="left", on="encounter_id"
    )
    refreshed_df["job"] = refreshed_df["job"].replace(abbreviated_job_map).str.upper()

    active_df = refreshed_df[refreshed_df["error_active"] == 1].copy()
    resolved_df = refreshed_df[refreshed_df["error_active"] == 0].copy()

    weekly_counts = (
        refreshed_df.groupby("error_week")
        .size()
        .reset_index(name="Count")
        .sort_values("error_week")
    )
    fig = px.bar(
        weekly_counts,
        x="error_week",
        y="Count",
        title="Weekly Error Counts",
        template="plotly_dark",
    )

    # Reuse the same build_table function as in show_errors
    active_table = build_table(active_df)
    resolved_table = build_table(resolved_df)

    return active_table, resolved_table, fig
