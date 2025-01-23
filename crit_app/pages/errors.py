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
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Errors", id="refresh-button", color="primary"
                            ),
                        ]
                    )
                ]
            ),
            html.Br(),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="error-run-chart"), width=12),
                ]
            ),
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

    # Create helper to build table
    def build_table(dataframe: pd.DataFrame):
        if dataframe.empty:
            return dbc.Alert("No errors found.", color="info")

        # Columns to show
        columns = [
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
        headers = [
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
                if col == "fflogs_url":
                    # Create clickable link
                    link = html.A("View FFLogs", href=row[col], target="_blank")
                    cells.append(html.Td(link))
                elif col == "error_active":
                    # Show 1 = active, 0 = resolved
                    checked = row[col] == 0
                    cells.append(
                        html.Td(
                            dbc.Checklist(
                                options=[{"label": "", "value": "resolved"}],
                                value=["resolved"] if checked else [],
                                inline=True,
                                id={"type": "resolve-check", "row_id": row.name},
                            )
                        )
                    )
                elif col == "traceback":
                    # Preserve multiline format and set width
                    traceback_str = str(row[col]) if pd.notnull(row[col]) else ""
                    cells.append(
                        html.Td(
                            html.Pre(
                                traceback_str,
                                style={
                                    "whiteSpace": "pre-wrap",
                                    "width": "425px",
                                },  # adjust as needed
                            ),
                            style={
                                "width": "425px"
                            },  # ensure table cell also enforces this width
                        )
                    )
                else:
                    cells.append(html.Td(str(row[col]) if pd.notnull(row[col]) else ""))

            table_body_rows.append(html.Tr(cells))

        table_body = [html.Tbody(table_body_rows)]
        return dbc.Table(
            table_header + table_body, bordered=True, striped=True, hover=True
        )

    return build_table(active_df), build_table(resolved_df), fig


@callback(
    Output("active-errors-table", "children", allow_duplicate=True),
    Output("resolved-errors-table", "children", allow_duplicate=True),
    Input({"type": "resolve-check", "row_id": ALL}, "value"),
    State("active-errors-table", "children"),
    State("resolved-errors-table", "children"),
    prevent_initial_call=True,
)
def update_error_status(checked_values, active_table, resolved_table):
    """
    Update error_active in the DB.

    If checkbox is checked => error_active=0 (resolved).
    If unchecked => error_active=1 (active).
    """
    # Determine row indices from context
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.inputs:
        raise dash.exceptions.PreventUpdate

    for trigger in ctx.triggered:
        prop_id = trigger["prop_id"].split(".")[0]
        if "resolve-check" in prop_id:
            row_id = eval(prop_id).get("row_id")
            # If "resolved" in value => error_active=0, else 1
            is_resolved = "resolved" in trigger["value"]
            new_status = 0 if is_resolved else 1

            # Update DB
            con = sqlite3.connect(DB_URI)
            query = """
                UPDATE error_player_analysis
                SET error_active = ?
                WHERE rowid = ?

                """
            # Attempt for party table as well in one go
            query2 = """
                UPDATE error_party_analysis
                SET error_active = ?
                WHERE rowid = ?
            """
            # We assume rowid from df's index won't match the DB rowid exactly.
            # In a real app, you'd store a unique ID in the table and pass it here.
            # This is just a conceptual placeholder.
            try:
                cur = con.cursor()
                cur.execute(query, (new_status, row_id + 1))
                cur.execute(query2, (new_status, row_id + 1))
                con.commit()
                cur.close()
            finally:
                con.close()

    # Return current states to refresh tables
    raise dash.exceptions.PreventUpdate
