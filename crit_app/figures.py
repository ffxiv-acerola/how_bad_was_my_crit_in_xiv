"""Functions to create figures and tables after a damage distributions are.

computed.
"""

from typing import Any, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table
from dash.dash_table import FormatTemplate
from dash.dash_table.Format import Format, Scheme
from plotly.graph_objs import Figure

from crit_app.dmg_distribution import get_dps_dmg_percentile

# Module level styling parameters
ACCENT_COLOR = "#FFA15A"  # Orange accent color for actual values
ACCENT_COLOR = "#F25F5C"  # Orange accent color for actual values


def make_rotation_pdf_figure(
    rotation_obj: Any, rotation_dps: float, active_dps_time: float, analysis_time: float
) -> Figure:
    """Make a plotly figure showing the DPS distribution for a rotation.

    The actual DPS for the run and first three moments of the DPS distribution are shown.

    Parameters:
        rotation_obj (Any): Rotation object from ffxiv_stats with damage distributions computed.
        rotation_dps (float): DPS actually dealt.
        active_dps_time (float): Elapsed time in seconds, used to convert damage dealt to DPS.
        analysis_time (float): Total analysis time.

    Returns:
        Figure: Plotly figure object displaying rotation DPS distribution.
    """
    t_div = active_dps_time / analysis_time
    support = rotation_obj.rotation_dps_support
    density = rotation_obj.rotation_dps_distribution
    if t_div == 1:
        pass
    else:
        support = support / t_div
        density = density * t_div

    max_density = density.max()
    x = support[density > max_density * 5e-6]
    x_min, x_max = x.min(), x.max()

    # Percentiles
    dx = support[1] - support[0]
    F_percentile = np.cumsum(density) * dx

    fig = px.line(template="plotly_dark")

    fig.add_scatter(
        x=support,
        y=density,
        name="DPS distribution",
        marker={"color": "#009670"},
        hovertext=[f"Percentile: {p:.1%}" for p in np.abs(F_percentile)],
        line=dict(width=3),  # Thicker line for better visibility
    )

    # Actual dps data points
    x = rotation_dps
    y = density[np.abs(support - x).argmin()]

    fig.add_scatter(
        x=[x],
        y=[y],
        mode="markers",
        name="Actual DPS",
        marker={"size": 14, "color": ACCENT_COLOR},
        hovertext=f"Percentile = {get_dps_dmg_percentile(x, density, support):.1f}%",
    )

    fig.update_xaxes(range=[x_min, x_max])

    mu = rotation_obj.rotation_mean / t_div
    sigma = rotation_obj.rotation_std / t_div
    fig.update_layout(
        title=f"Rotation DPS distribution: μ = {mu:.0f} DPS, σ = {sigma:.0f} DPS, γ = {rotation_obj.rotation_skewness:.3f}",
        xaxis_title=dict(
            text="Damage per second (DPS)",
            font=dict(size=16, family="Arial, sans-serif"),
        ),
        yaxis_title=dict(
            text="Frequency",
            font=dict(size=16, family="Arial, sans-serif"),
        ),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=0.97, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,20,0.8)",
        font=dict(family="Arial, sans-serif"),
        xaxis=dict(
            gridcolor="rgba(80,80,80,0.2)",
            titlefont=dict(size=16),
            tickfont=dict(size=14),
        ),
        yaxis=dict(
            gridcolor="rgba(80,80,80,0.2)",
            titlefont=dict(size=16),
            tickfont=dict(size=14),
        ),
        margin=dict(l=40, r=40, t=80, b=40),
        hoverlabel=dict(
            bgcolor="rgba(30,30,30,0.95)",
            font_color="white",
            bordercolor="rgba(50,50,50,0.95)",
        ),
    )

    # Add rounded corners via shape outlines
    fig.update_layout(
        shapes=[
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=1,
                y1=1,
                line=dict(width=0),
                fillcolor="rgba(0,0,0,0)",
            )
        ]
    )

    return fig


def make_rotation_percentile_table(
    rotation_obj: Any, rotation_percentile: float
) -> List[dash_table.DataTable]:
    """Make a table showing percentiles and corresponding DPS values for the.

    rotation DPS distribution.

    The actual DPS dealt and percentile is also shown, highlighted in green.

    Parameters:
        rotation_obj (Any): Rotation object from ffxiv_stats with damage distributions computed.
        rotation_percentile (float): Percentile of the actual DPS dealt.

    Returns:
        List[dash_table.DataTable]: A list containing a Dash table.
    """
    percentiles = sorted(
        [0.1, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999] + [rotation_percentile]
    )
    percentiles = np.array(percentiles)

    t_div = rotation_obj.active_dps_t / rotation_obj.analysis_t

    support = rotation_obj.rotation_dps_support
    density = rotation_obj.rotation_dps_distribution

    if t_div > 1:
        support /= t_div
        density = density / np.trapz(density, support)

    dx = support[1] - support[0]
    F = np.cumsum(density) * dx
    percentile_idx = np.abs(F - percentiles[:, np.newaxis]).argmin(axis=1)

    rotation_percentile_df = pd.DataFrame(
        {
            "Percentile": percentiles,
            "DPS": support[percentile_idx],
        }
    )

    # Modern styling for the table matching analysis_history.py
    style_rotation_percentile = [
        {
            "if": {"filter_query": "{{Percentile}} = {}".format(rotation_percentile)},
            "backgroundColor": "#009670",
            "color": "white",
            "fontWeight": "bold",
        },
        # Hover state styling
        {
            "if": {"state": "selected"},
            "backgroundColor": "inherit",
            "border": "inherit",
        },
    ]

    percentile_format = FormatTemplate.percentage(1)
    columns = [
        dict(
            id="Percentile", name="Percentile", type="numeric", format=percentile_format
        ),
        dict(
            id="DPS",
            name="DPS",
            type="numeric",
            format=Format(precision=2, scheme=Scheme.decimal_integer),
        ),
    ]

    rotation_percentile_table = [
        dash_table.DataTable(
            data=rotation_percentile_df.to_dict("records"),
            columns=columns,
            cell_selectable=False,
            style_data_conditional=style_rotation_percentile,
            style_header={
                "backgroundColor": "#222",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "left",
                "border": "none",
                "borderBottom": "1px solid #333",
                "padding": "10px 15px",
                "fontFamily": "sans-serif",
            },
            style_data={
                "backgroundColor": "#333",
                "color": "white",
                "textAlign": "left",
                "padding": "10px 15px",
                "fontFamily": "sans-serif",
                "border": "none",
                "borderBottom": "1px solid #292929",
            },
            style_table={
                "overflowX": "auto",
                "borderRadius": "5px",
                "overflow": "hidden",
                "boxShadow": "0 3px 6px rgba(0,0,0,0.16)",
            },
            style_cell={
                "textAlign": "left",
                "padding": "10px 15px",
                "fontFamily": "sans-serif",
                "border": "none",
                "borderBottom": "1px solid #292929",
                "userSelect": "none",
            },
            css=[
                {
                    "selector": ".dash-spreadsheet",
                    "rule": "font-family: sans-serif; border-radius: 5px; overflow: hidden; box-shadow: 0 3px 6px rgba(0,0,0,0.16);",
                },
                {
                    "selector": ".dash-table-container .dash-spreadsheet td, .dash-table-container .dash-spreadsheet th",
                    "rule": "border-color: #292929 !important;",
                },
                {
                    "selector": ".dash-spreadsheet tr:last-child td",
                    "rule": "border-bottom: none !important;",
                },
                {
                    "selector": ".dash-cell-value",
                    "rule": "caret-color: transparent !important;",
                },
            ],
        )
    ]
    return rotation_percentile_table


def how_tall_should_the_action_box_plot_be(n_actions: int) -> int:
    """Alter height of the box figure so it can fit and look good.

    More actions and the width of a single bar chart.

    Args:
        n_actions (int): Number of total actions being plotted.

    Returns:
        int: Approximate height of each bar chart in pixels.
    """
    if n_actions <= 7:
        return 105
    elif (n_actions > 7) & (n_actions <= 10):
        return 85
    elif (n_actions > 10) & (n_actions <= 15):
        return 65
    elif (n_actions > 15) & (n_actions <= 20):
        return 55
    else:
        return 45


def make_action_box_and_whisker_figure(
    rotation_data: Any,
    action_dps: pd.DataFrame,
    active_dps_time: float,
    analysis_time: float,
) -> Figure:
    """Show DPS distributions for actions as a collection of box and whisker.

    plots.

    Parameters:
        rotation_data (Any): Rotation data object containing unique actions distribution.
        action_dps (pd.DataFrame): DataFrame containing action DPS values.
        active_dps_time (float): Elapsed time in seconds, used to convert damage dealt to DPS.
        analysis_time (float): Total analysis time.

    Returns:
        Figure: Plotly figure object displaying action DPS distributions.
    """
    t_div = active_dps_time / analysis_time

    n_actions = len(rotation_data.unique_actions_distribution)
    l_fence = np.zeros(shape=(n_actions))
    q1 = np.zeros(shape=(n_actions))
    q2 = np.zeros(shape=(n_actions))
    q3 = np.zeros(shape=(n_actions))
    u_fence = np.zeros(shape=(n_actions))
    uu_fence = np.zeros(shape=(n_actions))  # 99th %
    y = np.zeros(shape=(n_actions))

    actual_dps = np.zeros(shape=(n_actions))
    actual_dps_percentile = np.zeros(shape=(n_actions))

    action_names = list(rotation_data.unique_actions_distribution.keys())

    # Loop through actions and compute percentiles for box plots
    for idx, (k, v) in enumerate(rotation_data.unique_actions_distribution.items()):
        if t_div == 1:
            density = v["dps_distribution"]
            support = v["support"]
        else:
            support = v["support"] / active_dps_time
            density = v["dps_distribution"] / np.trapz(v["dps_distribution"], support)

        # Percentiles
        dx = support[1] - support[0]
        F_percentile = np.cumsum(density) * dx

        y[idx] = idx
        l_fence[idx] = int(support[np.abs(F_percentile - 0.10).argmin()])
        q1[idx] = int(support[np.abs(F_percentile - 0.25).argmin()])
        q2[idx] = int(support[np.abs(F_percentile - 0.5).argmin()])
        q3[idx] = int(support[np.abs(F_percentile - 0.75).argmin()])
        u_fence[idx] = int(support[np.abs(F_percentile - 0.90).argmin()])
        uu_fence[idx] = int(support[np.abs(F_percentile - 0.99).argmin()])

        actual_dps[idx] = action_dps.loc[
            action_dps["ability_name"] == k, "amount"
        ].iloc[0]
        actual_dps_percentile[idx] = F_percentile[
            np.abs(actual_dps[idx] - support).argmin()
        ]

    # Order by descending median
    idx_order = np.argsort(q2)
    ytick_labels = {int(idx): action_names[a] for idx, a in enumerate(idx_order)}

    box_percentiles = {
        "lowerfence": l_fence[idx_order],
        "q1": q1[idx_order],
        "median": q2[idx_order],
        "q3": q3[idx_order],
        "upperfence": u_fence[idx_order],
    }

    # Hover styling
    custom_data = pd.DataFrame(box_percentiles)
    custom_data["95th_percentile"] = uu_fence[idx_order]
    custom_data["actual_percentile"] = actual_dps_percentile[idx_order]
    custom_data["name"] = list(ytick_labels.values())
    hovertemplate_text = (
        "<b>%{customdata[7]}</b><br><br>" + "Actual DPS: %{x:,.0f} DPS<br>"
        "Percentile: %{customdata[6]:.1%}<br><br>"
        "10th %: %{customdata[0]:,.0f} DPS<br>"
        + "25th %: %{customdata[1]:,.0f} DPS<br>"
        + "50th %: %{customdata[2]:,.0f} DPS<br>"
        + "75th %: %{customdata[3]:,.0f} DPS<br>"
        + "90th %: %{customdata[4]:,.0f} DPS<br>"
        + "99th %: %{customdata[5]:,.0f} DPS<br>"
    )

    # Actual figure time
    layout = go.Layout(
        template="plotly_dark",
        height=n_actions * how_tall_should_the_action_box_plot_be(n_actions),
    )
    fig = go.Figure(layout=layout)

    # Box plots
    fig.add_trace(
        go.Box(
            y=list(range(n_actions)),
            name="DPS Distribution",
            marker_color="#009670",
            hoverinfo="skip",
            boxmean=True,  # Show the mean as a dashed line
            boxpoints=False,  # Don't show outliers
            line=dict(width=2),  # Thicker box lines
            fillcolor="rgba(0, 150, 112, 0.4)",  # Semi-transparent fill
            **box_percentiles,
        )
    )

    # Actual DPS as points
    fig.add_trace(
        go.Scatter(
            x=actual_dps[idx_order],
            y=list(range(n_actions)),
            mode="markers",
            name="Actual DPS",
            marker=dict(
                size=9,
                color=ACCENT_COLOR,
                line=dict(width=1, color="#FF8C00"),
                symbol="diamond",
            ),
            customdata=custom_data,
            hovertemplate=hovertemplate_text,
        )
    )

    fig.update_yaxes(
        labelalias=ytick_labels,
        dtick=1,
        range=[-0.5, n_actions - 0.5],
        gridcolor="rgba(80,80,80,0.2)",
        tickfont=dict(size=14),
    )
    fig.update_xaxes(
        title=dict(
            text="Damage per second (DPS)",
            font=dict(size=16, family="Arial, sans-serif"),
        ),
        gridcolor="rgba(80,80,80,0.2)",
        tickfont=dict(size=14),
    )

    # Title and place the legend at the top
    # Horizontal space much more constrained than vertical.
    fig.update_layout(
        title="DPS distributions by action",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(20,20,20,0.8)",  # Darker background
        font=dict(family="Arial, sans-serif"),
        margin=dict(l=40, r=40, t=80, b=40),
        hoverlabel=dict(
            bgcolor="rgba(30,30,30,0.95)",
            font_color="white",
            bordercolor="rgba(50,50,50,0.95)",
        ),
    )
    return fig


def make_action_pdfs_figure(
    rotation_obj: Any,
    action_dps: pd.DataFrame,
    active_dps_time: float,
    analysis_time: float,
) -> Figure:
    """Plot damage distributions for each action.

    The actual damage dealt is also plotted.

    Parameters:
        rotation_obj (Any): Rotation object from ffxiv_stats with damage distributions computed.
        action_dps (pd.DataFrame): DataFrame with columns "ability_name" and "amount".
        active_dps_time (float): Elapsed time in seconds, used to convert damage dealt to DPS.
        analysis_time (float): Total analysis time.

    Returns:
        Figure: Plotly figure with action DPS distributions plotted.
    """
    t_div = active_dps_time / analysis_time
    fig = px.line(template="plotly_dark")

    # Attempt at auto setting x and y limits
    max_y = []
    colors = {}  # Color coordination betw actual DPS and DPS pdf

    x_max = []
    x_min = []

    max_density = rotation_obj.rotation_dps_distribution.max()

    for idx, (k, v) in enumerate(rotation_obj.unique_actions_distribution.items()):
        if t_div == 1:
            density = v["dps_distribution"]
            support = v["support"]
        else:
            support = v["support"] / active_dps_time
            density = v["dps_distribution"] / np.trapz(v["dps_distribution"], support)

        dx = support[1] - support[0]
        F_percentile = np.cumsum(density) * dx

        color_idx = idx % len(px.colors.qualitative.Plotly)
        fig.add_trace(
            go.Scatter(
                x=support,
                y=density,
                name=k,
                mode="lines",
                legendgroup="Action name",
                legendgrouptitle_text="Action Name",
                marker={"color": px.colors.qualitative.Plotly[color_idx]},
                visible=True,
                hovertext=[f"Percentile: {p:.1%}" for p in np.abs(F_percentile)],
            )
        )

        x = action_dps.loc[action_dps["ability_name"] == k, "amount"].iloc[0]
        y = density[np.abs(support - x).argmin()]

        fig.add_scatter(
            x=np.array([x]),
            y=np.array([y]),
            name=f"{k} (Actual DPS)",
            mode="markers",
            legendgroup="Actual DPS",
            legendgrouptitle_text="Actual DPS",
            marker={"color": px.colors.qualitative.Plotly[color_idx], "size": 11},
            hovertext=f"Percentile = {get_dps_dmg_percentile(x, density, support):.1f}%",
            visible=True,
        )

        max_density = density.max()
        max_y.append(max_density)
        truncated_x = support[density > max_density * 5e-6]
        x_min.append(truncated_x[0])
        x_max.append(truncated_x[-1])
        colors[k] = px.colors.qualitative.Plotly[color_idx]

    fig.update_layout(
        title="DPS distribution by unique action",
        xaxis_title="Damage per second (DPS)",
        yaxis_title="Frequency",
    )

    # First attempt at auto scaling axes, might need to be updated.
    fig.update_yaxes(range=[-min(max_y) / 10, min(max_y) * 5])
    fig.update_xaxes(range=[min(x_min) - (max(x_max) - min(x_min)) / 50, max(x_max)])

    return fig


def make_kill_time_graph(
    party_rotation_dataclass: Any, kill_time_seconds: int
) -> Figure:
    """Make a plotly figure showing the kill time graph for a party rotation.

    The actual kill time and theoretical kill times are shown.

    Parameters:
        party_rotation_dataclass (Any): Party rotation data class containing shortened rotations and percentiles.
        kill_time_seconds (int): Actual kill time in seconds.

    Returns:
        Figure: Plotly figure object displaying the kill time graph.
    """
    # Phase-aware kill time
    kill_time_seconds = party_rotation_dataclass.fight_duration
    x = [
        kill_time_seconds - x.seconds_shortened
        for x in party_rotation_dataclass.shortened_rotations
    ]
    x_theoretical = [
        f"2024-01-01 00:{int(x//60):02}:{int(x%60):02}.{int(round((x % 60 % 1) * 1000, 0))}"
        for x in x
    ]

    y_theoretical = [
        (1 - y.percentile) for y in party_rotation_dataclass.shortened_rotations
    ]

    x_real = [
        f"2024-01-01 00:{int(kill_time_seconds//60):02}:{int(kill_time_seconds%60):02}.{int(round((kill_time_seconds % 60 % 1) * 1000, 0))}"
    ]
    y_real = [(1 - party_rotation_dataclass.percentile)]

    y_min, y_max = (np.floor(np.log10(y_theoretical)) - 1).min(), 1e-2

    layout = go.Layout(
        yaxis=dict(range=[y_min, y_max], type="log", tickformat="%"),
        xaxis=dict(tickformat=r"%M:%S.%L"),
        xaxis_title=dict(text="Kill time (KT)"),
        yaxis_title=dict(text="% of kills faster than KT"),
        template="plotly_dark",
    )

    df_theoretical = pd.DataFrame(
        {"kill_time": x_theoretical, "percent_kills_faster": y_theoretical}
    )
    df = pd.DataFrame({"kill_time": x_real, "percent_kills_faster": y_real})

    hovertemplate_text = (
        "<b>Kill time: %{x}</b><br><br>" "% of kills faster than %{x}: %{y}"
    )

    fig = go.Figure(
        data=[
            go.Bar(
                x=df["kill_time"],
                y=df[r"percent_kills_faster"],
                marker_color="#7b6cb2",
                marker_line_color="#7b6cb2",
                name="Actual KT",
                hovertemplate=hovertemplate_text,
            ),
            go.Bar(
                x=df_theoretical["kill_time"],
                y=df_theoretical[r"percent_kills_faster"],
                marker_color="#009670",
                marker_line_color="#009670",
                name="Theoretical KT",
                hovertemplate=hovertemplate_text,
            ),
        ],
        layout=layout,
    )

    fig.update_yaxes(tickformat=".2%")
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)

    return fig


def make_party_rotation_pdf_figure(party_analysis_data: Any) -> Figure:
    """Make a plotly figure showing the DPS distribution for a party rotation.

    The actual DPS for the run and first three moments of the DPS distribution are shown.

    Parameters:
        party_analysis_data (Any): Party analysis data object containing damage distributions.

    Returns:
        Figure: Plotly figure object displaying party rotation DPS distribution.
    """
    boss_hp = party_analysis_data.boss_hp
    party_support = party_analysis_data.party_damage_support
    party_pdf = party_analysis_data.party_damage_distribution
    t = party_analysis_data.active_dps_time

    party_support /= t
    party_pdf = party_pdf / np.trapz(party_pdf, party_support)

    max_density = party_pdf.max()
    x_lim = party_support[party_pdf > max_density * 5e-6]
    x_min, x_max = x_lim[0], x_lim[-1]

    party_dps_x = boss_hp / t
    party_dps_y = party_pdf[np.abs(party_support - party_dps_x).argmin()]

    dx = party_support[1] - party_support[0]
    F_percentile = np.cumsum(party_pdf) * dx

    layout = go.Layout(
        xaxis=dict(range=[x_min, x_max]),
        xaxis_title={"text": "Damage per second (DPS)"},
        yaxis_title={"text": "Frequency"},
        template="plotly_dark",
    )

    fig = go.Figure(
        data=[
            go.Scatter(
                x=party_support,
                y=party_pdf,
                mode="lines",
                marker={"color": "#009670"},
                name="DPS distribution",
                hovertext=[f"Percentile: {p:.1%}" for p in np.abs(F_percentile)],
            ),
            go.Scatter(
                x=[party_dps_x],
                y=[party_dps_y],
                marker={"size": 14, "color": ACCENT_COLOR},
                name="Actual DPS",
                hovertext=f"Percentile: {F_percentile[np.abs(party_support - party_dps_x).argmin()]:.1%}",
            ),
        ],
        layout=layout,
    )

    mu = party_analysis_data.party_mean / t
    sigma = party_analysis_data.party_std / t
    skew = party_analysis_data.party_skewness
    fig.update_layout(
        title=f"Party rotation DPS distribution: μ = {mu:.0f} DPS, σ = {sigma:.0f} DPS, γ = {skew:.3f}",
        xaxis_title="Damage per second (DPS)",
        yaxis_title="Frequency",
    )

    return fig
