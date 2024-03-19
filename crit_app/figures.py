"""
Functions to create figures and tables after a damage distributions are computed.
"""

import plotly.express as px
import plotly.graph_objects as go

from dash import dash_table
from dash.dash_table import FormatTemplate
from dash.dash_table.Format import Format, Scheme

import pandas as pd
import numpy as np

from dmg_distribution import get_dmg_percentile, summarize_actions


def make_rotation_pdf_figure(rotation_obj, rotation_dps):
    """
    Make a plotly figure showing the DPS distribution for a rotation.
    The actual DPS for the run and first three moments of the DPS distribution are shown.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    rotation_dps - float, DPS actually dealt.

    Returns:
    plotly figure object displaying rotation DPS distribution
    """
    max_density = rotation_obj.rotation_dps_distribution.max()
    x = rotation_obj.rotation_dps_support[
        rotation_obj.rotation_dps_distribution > max_density * 5e-6
    ]
    x_min, x_max = x[0], x[-1]

    fig = px.line(template="plotly_dark")

    fig.add_scatter(
        x=rotation_obj.rotation_dps_support,
        y=rotation_obj.rotation_dps_distribution,
        name="DPS distribution",
        marker={"color": "#009670"},
    )

    x = rotation_dps
    y = rotation_obj.rotation_dps_distribution[
        np.abs(rotation_obj.rotation_dps_support - x).argmin()
    ]

    fig.add_scatter(
        x=[x],
        y=[y],
        mode="markers",
        name="Actual DPS",
        marker={"size": 14, "color": "#009670"},
        hovertext=f"Percentile = {get_dmg_percentile(x, rotation_obj.rotation_dps_distribution, rotation_obj.rotation_dps_support):.1f}%",
    )

    fig.update_xaxes(range=[x_min, x_max])
    fig.update_layout(
        title=f"Rotation DPS distribution: μ = {rotation_obj.rotation_mean:.0f} DPS, σ = {rotation_obj.rotation_std:.0f} DPS, γ = {rotation_obj.rotation_skewness:.3f}",
        xaxis_title="Damage per second (DPS)",
        yaxis_title="Frequency",
    )

    return fig


def make_rotation_percentile_table(rotation_obj, rotation_percentile):
    """
    Make a table showing percentiles and corresponding DPS values for the rotation DPS distribution.
    The actual DPS dealt and percentile is also shown, highlighted in green.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    rotation_dps - float, DPS actually dealt.

    Returns:
    list containing a Dash table
    """
    percentiles = sorted(
        [0.1, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999] + [rotation_percentile]
    )
    percentiles = np.array(percentiles)
    dx = rotation_obj.rotation_dps_support[1] - rotation_obj.rotation_dps_support[0]
    F = np.cumsum(rotation_obj.rotation_dps_distribution) * dx
    percentile_idx = np.abs(F - percentiles[:, np.newaxis]).argmin(axis=1)

    rotation_percentile_df = pd.DataFrame(
        {
            "Percentile": percentiles,
            "DPS": rotation_obj.rotation_dps_support[percentile_idx],
        }
    )
    style_rotation_percentile = [
        {
            "if": {"filter_query": "{{Percentile}} = {}".format(rotation_percentile)},
            "backgroundColor": "#009670",
        }
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
                'backgroundColor': 'rgb(48, 48, 48)',
                'color': 'white'
            },
            style_data={
                'backgroundColor': 'rgb(50, 50, 50)',
                'color': 'white'
            },
        )
    ]
    return rotation_percentile_table


def make_action_pdfs_figure(rotation_obj, action_dps):
    """
    Plot damage distributions for each action.
    The actual damage dealt is also plotted.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    action_dps - pd DataFrame with columns "ability_name" and "amount"

    Returns:
    Plotly figure with action DPS distributions plotted
    """
    fig = px.line(template="plotly_dark")

    # Attempt at auto setting x and y limits
    max_y = []
    colors = {}  # Color coordination betw actual DPS and DPS pdf

    x_max = []
    x_min = []

    max_density = rotation_obj.rotation_dps_distribution.max()

    for idx, (k, v) in enumerate(rotation_obj.unique_actions_distribution.items()):
        color_idx = idx % len(px.colors.qualitative.Plotly)
        fig.add_trace(
            go.Scatter(
                x=v["support"],
                y=v["dps_distribution"],
                name=k,
                mode="lines",
                legendgroup="Action name",
                legendgrouptitle_text="Action Name",
                marker={"color": px.colors.qualitative.Plotly[color_idx]},
            )
        )

        x = action_dps.loc[action_dps["ability_name"] == k, "amount"].iloc[0]
        y = v["dps_distribution"][np.abs(v["support"] - x).argmin()]

        fig.add_scatter(
            x=[x],
            y=[y],
            name=k,
            mode="markers",
            legendgroup="Actual DPS",
            legendgrouptitle_text="Actual DPS",
            marker={"color": px.colors.qualitative.Plotly[color_idx], "size": 11},
            hovertext=f"Percentile = {get_dmg_percentile(x, v['dps_distribution'], v['support']):.1f}%",
        )

        max_density = v["dps_distribution"].max()
        max_y.append(max_density)
        truncated_x = v["support"][v["dps_distribution"] > max_density * 5e-6]
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


def make_action_table(rotation_obj, action_df, t):
    """
    Create a table listing an action name, expected DPS, actual DPS dealt, and the corresponding percentile.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    action_df - pd DataFrame of actions, obtained the function `create_action_df`, which depends on output from `damage_events`.
    t - float, time used to compute DPS from damage.

    Outputs:
    list containing a Dash table with action, expected dps, actual dps, and percentile.
    """
    action_summary_df = summarize_actions(
        action_df, rotation_obj.unique_actions_distribution, t
    ).sort_values("actual_dps_dealt", ascending=False)
    action_summary_df = action_summary_df.rename(
        columns={
            "ability_name": "Action",
            "expected_dps": "Expected DPS (mean)",
            "actual_dps_dealt": "Actual DPS",
            "percentile": "Percentile",
        }
    )
    columns = [
        dict(
            id="Action",
            name="Action",
        ),
        dict(
            id="Expected DPS (mean)",
            name="Expected DPS (mean)",
            type="numeric",
            format=Format(precision=2, scheme=Scheme.decimal_integer),
        ),
        dict(
            id="Actual DPS",
            name="Actual DPS",
            type="numeric",
            format=Format(precision=2, scheme=Scheme.decimal_integer),
        ),
        dict(
            id="Percentile",
            name="Percentile",
            type="numeric",
            format=FormatTemplate.percentage(1),
        ),
    ]
    print(action_summary_df.to_dict("records"))
    action_summary_table = [
        dash_table.DataTable(
            data=action_summary_df.to_dict("records"),
            columns=columns,
            cell_selectable=False,
            style_header={
                'backgroundColor': 'rgb(48, 48, 48)',
                'color': 'white'
            },
            style_data={
                'backgroundColor': 'rgb(50, 50, 50)',
                'color': 'white'
            },
        )
    ]
    return action_summary_table
