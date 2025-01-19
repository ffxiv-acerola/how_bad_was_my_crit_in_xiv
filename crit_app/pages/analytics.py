import sqlite3
from typing import Optional
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Input, Output, callback, dcc, html

dash.register_page(
    __name__,
    path="/analytics",
)


def analytics_query() -> pd.DataFrame:
    """
    Retrieve analytics data from the database, merge with encounter information, and return a DataFrame.

    Returns:
        pd.DataFrame: Combined analytics data.
    """
    conn = sqlite3.connect("reports.db")

    query = """
    SELECT
        cpa.analysis_id,
        cpa.creation_ts,
		DATE(creation_ts, '-' || ((CAST(strftime('%w', creation_ts) AS INTEGER) + 6) % 7) || ' days') AS week_start,
        e.encounter_id,
        e.role,
        e.job,
        e.player_server as region
    FROM creation_player_analysis cpa
    LEFT JOIN report r USING (analysis_id)
    LEFT JOIN encounter e USING (report_id, fight_id, player_name)
    where creation_ts is not null
    """

    # Read the query into a DataFrame
    df = pd.read_sql_query(query, conn)
    df = df.merge(encounter_information_df, how="left", on="encounter_id")
    df["region"] = df["region"].replace(world_to_region)
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["creation_ts"] = pd.to_datetime(df["creation_ts"])
    # Close the connection
    conn.close()
    return df


def compute_encounter_counts(
    df: pd.DataFrame, patch_filter: Optional[str] = None
) -> pd.DataFrame:
    """
    Compute the encounter frequencies based on optional patch filtering.

    Args:
        df (pd.DataFrame): The input DataFrame containing analytics data.
        patch_filter (str, optional): Patch string for filtering, e.g. '6.4 - 6.5'.

    Returns:
        pd.DataFrame: A DataFrame with encounter frequencies.
    """
    if patch_filter is not None:
        filtered_df = df[df["relevant_patch"] == patch_filter]
    else:
        filtered_df = df

    return (
        filtered_df.groupby(["encounter_name", "content_type", "encounter_id"])
        .size()
        .reset_index(name="Count")
        .sort_values(["content_type", "encounter_id"])
        .rename(
            columns={"encounter_name": "Encounter name", "content_type": "Content type"}
        )[["Encounter name", "Content type", "Count"]]
    )


def compute_role_job_counts(
    df: pd.DataFrame, patch_filter: Optional[str] = None
) -> pd.DataFrame:
    """
    Compute role and job frequencies with optional patch filtering.

    Args:
        df (pd.DataFrame): The input DataFrame.
        patch_filter (str, optional): Patch string for filtering results.

    Returns:
        pd.DataFrame: A DataFrame showing counts by role and job.
    """
    if patch_filter is not None:
        filtered_df = df[df["relevant_patch"] == patch_filter]
    else:
        filtered_df = df
    return (
        filtered_df.groupby(["role", "job"]).size().reset_index(name="Analysis Count")
    )


def compute_region_counts(
    df: pd.DataFrame, patch_filter: Optional[str] = None
) -> pd.DataFrame:
    """
    Compute region frequencies with optional patch filtering.

    Args:
        df (pd.DataFrame): The input DataFrame.
        patch_filter (str, optional): Patch string for filtering results.

    Returns:
        pd.DataFrame: A DataFrame showing counts by region.
    """
    if patch_filter is not None:
        filtered_df = df[df["relevant_patch"] == patch_filter]
    else:
        filtered_df = df
    return filtered_df.groupby(["region"]).size().reset_index(name="Analysis Count")


def layout():
    # Always default to the latest patch
    default_patch_idx = max(patch_values.keys())

    analytics_df = analytics_query()

    # Group by start-of-week
    weekly_counts = analytics_df.groupby("week_start").size().reset_index(name="count")

    analysis_run_chart = dcc.Graph(
        figure=px.bar(
            weekly_counts,
            x="week_start",
            y="count",
            title="Weekly Analysis Counts",
            template="plotly_dark",
        ),
    )

    encounter_counts = compute_encounter_counts(analytics_df, default_patch_idx)
    encounter_count_table = dbc.Table.from_dataframe(
        encounter_counts, striped=True, bordered=True, hover=True
    )

    #### By job
    role_job_counts = compute_role_job_counts(analytics_df, default_patch_idx)

    role_job_graph = dcc.Graph(
        figure=px.bar(
            role_job_counts,
            x="role",
            y="Analysis Count",
            color="job",
            text="job",
            barmode="stack",
            template="plotly_dark",
        )
    )

    region_counts = compute_region_counts(analytics_df, default_patch_idx)

    region_graph = dcc.Graph(
        figure=px.bar(
            region_counts, x="region", y="Analysis Count", template="plotly_dark"
        )
    )
    analytic_row = dbc.Row(
        [
            dbc.Col(html.Div(role_job_graph), md=8, width=12),
            dbc.Col(html.Div(region_graph), md=4, width=12),
        ]
    )
    select_label = dbc.Label("Patch filter:")
    selector = dbc.Select(id="patch-selector", options=selector_options, value=1)

    # Encounter table placeholder
    encounter_count_table = html.Div(id="encounter-table")

    # Region graph placeholder
    region_graph = dcc.Graph(id="region-graph")

    # Role-job graph placeholder
    role_job_graph = dcc.Graph(id="role-job-graph")

    run_chart_row = dbc.Row(
        [
            dbc.Col(html.Div(analysis_run_chart), md=8, width=12),
            dbc.Col(
                html.Div([select_label, selector, encounter_count_table]),
                md=4,
                width=12,
            ),
        ]
    )

    analytic_row = dbc.Row(
        [
            dbc.Col(html.Div(role_job_graph), md=8, width=12),
            dbc.Col(html.Div(region_graph), md=4, width=12),
        ]
    )

    return [run_chart_row, html.Br(), analytic_row]


@callback(
    Output("encounter-table", "children"),
    Output("region-graph", "figure"),
    Output("role-job-graph", "figure"),
    Input("patch-selector", "value"),
)
def update_charts(patch_idx):
    if isinstance(patch_idx, str):
        try:
            patch_idx = int(patch_idx)
        except Exception:
            dash.exceptions.PreventUpdate()

    if patch_idx is None or patch_idx < 0:
        dash.exceptions.PreventUpdate()
    selected_patch_str = patch_values[patch_idx]

    # 2. Retrieve or reprocess your main DataFrame
    analytics_df = analytics_query()

    # 3. Encounter counts
    encounter_counts = compute_encounter_counts(analytics_df, selected_patch_str)

    # Build a new HTML table
    encounter_table = dbc.Table.from_dataframe(
        encounter_counts, striped=True, bordered=True, hover=True
    )

    # 4. Region counts
    region_counts = compute_region_counts(analytics_df, selected_patch_str)
    fig_region = px.bar(
        region_counts,
        x="region",
        y="Analysis Count",
        template="plotly_dark",
        title="Region Counts",
    )

    # 5. Role-job counts
    role_job_counts = compute_role_job_counts(analytics_df, selected_patch_str)

    fig_role_job = px.bar(
        role_job_counts,
        x="role",
        y="Analysis Count",
        color="job",
        text="job",
        barmode="stack",
        template="plotly_dark",
        title="Role-Job Counts",
    )

    # Return all three outputs in order
    return encounter_table, fig_region, fig_role_job


encounter_information = [
    {
        "encounter_id": 88,
        "encounter_name": "Kokytos",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 89,
        "encounter_name": "Pandaemonium",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 90,
        "encounter_name": "Themis",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 91,
        "encounter_name": "Athena",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 92,
        "encounter_name": "Pallas Athena",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 93,
        "encounter_name": "Black Cat",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 94,
        "encounter_name": "Honey B. Lovely",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 95,
        "encounter_name": "Brute Bomber",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 96,
        "encounter_name": "Wicked Thunder",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1069,
        "encounter_name": "Golbez",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1070,
        "encounter_name": "Zeromus",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1072,
        "encounter_name": "Zoraal Ja",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1078,
        "encounter_name": "Queen Eternal",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1079,
        "encounter_name": "Futures Rewritten",
        "content_type": "Ultimate",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 3009,
        "encounter_name": "Byakko",
        "content_type": "Unreal",
        "relevant_patch": "7.0 - 7.2",
    },
]
encounter_information_df = pd.DataFrame(encounter_information)
patch_values = {
    idx: a for idx, a in enumerate(set(encounter_information_df["relevant_patch"]))
}
patch_values[-1] = None
selector_options = [
    {"label": v if v is not None else "All", "value": k}
    for k, v in patch_values.items()
]

world_to_region = {
    # North America
    "Adamantoise": "North America",
    "Cactuar": "North America",
    "Faerie": "North America",
    "Gilgamesh": "North America",
    "Jenova": "North America",
    "Midgardsormr": "North America",
    "Sargatanas": "North America",
    "Siren": "North America",
    "Balmung": "North America",
    "Brynhildr": "North America",
    "Coeurl": "North America",
    "Diabolos": "North America",
    "Goblin": "North America",
    "Malboro": "North America",
    "Mateus": "North America",
    "Zalera": "North America",
    "Cuchulainn": "North America",
    "Golem": "North America",
    "Halicarnassus": "North America",
    "Kraken": "North America",
    "Maduin": "North America",
    "Marilith": "North America",
    "Rafflesia": "North America",
    "Seraph": "North America",
    "Behemoth": "North America",
    "Excalibur": "North America",
    "Exodus": "North America",
    "Famfrit": "North America",
    "Hyperion": "North America",
    "Lamia": "North America",
    "Leviathan": "North America",
    "Ultros": "North America",
    # Europe
    "Cerberus": "Europe",
    "Louisoix": "Europe",
    "Moogle": "Europe",
    "Omega": "Europe",
    "Phantom": "Europe",
    "Ragnarok": "Europe",
    "Sagittarius": "Europe",
    "Spriggan": "Europe",
    "Alpha": "Europe",
    "Lich": "Europe",
    "Odin": "Europe",
    "Phoenix": "Europe",
    "Raiden": "Europe",
    "Shiva": "Europe",
    "Twintania": "Europe",
    "Zodiark": "Europe",
    # Oceania
    "Bismarck": "Oceania",
    "Ravana": "Oceania",
    "Sephirot": "Oceania",
    "Sophia": "Oceania",
    "Zurvan": "Oceania",
    # Japan
    "Aegis": "Japan",
    "Atomos": "Japan",
    "Carbuncle": "Japan",
    "Garuda": "Japan",
    "Gungnir": "Japan",
    "Kujata": "Japan",
    "Ramuh": "Japan",
    "Tonberry": "Japan",
    "Typhon": "Japan",
    "Unicorn": "Japan",
    "Alexander": "Japan",
    "Bahamut": "Japan",
    "Durandal": "Japan",
    "Fenrir": "Japan",
    "Ifrit": "Japan",
    "Ridill": "Japan",
    "Tiamat": "Japan",
    "Ultima": "Japan",
    "Valefor": "Japan",
    "Yojimbo": "Japan",
    "Zeromus": "Japan",
    "Anima": "Japan",
    "Asura": "Japan",
    "Chocobo": "Japan",
    "Hades": "Japan",
    "Ixion": "Japan",
    "Masamune": "Japan",
    "Pandaemonium": "Japan",
    "Shinryu": "Japan",
    "Titan": "Japan",
    "Belias": "Japan",
    "Kaguya": "Japan",
}
