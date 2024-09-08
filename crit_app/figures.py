"""
Functions to create figures and tables after a damage distributions are computed.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table
from dash.dash_table import FormatTemplate
from dash.dash_table.Format import Format, Scheme
from dmg_distribution import get_dps_dmg_percentile, summarize_actions


def make_rotation_pdf_figure(
    rotation_obj, rotation_dps, active_dps_time, analysis_time
):
    """
    Make a plotly figure showing the DPS distribution for a rotation.
    The actual DPS for the run and first three moments of the DPS distribution are shown.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    rotation_dps - float, DPS actually dealt.
    active_dps_time - float, elapsed time in seconds, used to convert damage dealt to DPS.

    Returns:
    plotly figure object displaying rotation DPS distribution
    """
    t_div = active_dps_time / analysis_time
    if t_div == 1:
        support = rotation_obj.rotation_dps_support
        density = rotation_obj.rotation_dps_distribution

    else:
        support = rotation_obj.rotation_dps_support / active_dps_time
        density = rotation_obj.rotation_dps_distribution / np.trapz(
            rotation_obj.rotation_dps_distribution, support
        )

    max_density = density.max()
    x = support[density > max_density * 5e-6]
    x_min, x_max = x[0], x[-1]

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
    )

    # Actual dps data points
    x = rotation_dps
    y = density[np.abs(support - x).argmin()]

    fig.add_scatter(
        x=[x],
        y=[y],
        mode="markers",
        name="Actual DPS",
        marker={"size": 14, "color": "#FFA15A"},
        hovertext=f"Percentile = {get_dps_dmg_percentile(x, density, support):.1f}%",
    )

    fig.update_xaxes(range=[x_min, x_max])

    mu = rotation_obj.rotation_mean / t_div
    sigma = rotation_obj.rotation_std / t_div
    fig.update_layout(
        title=f"Rotation DPS distribution: μ = {mu:.0f} DPS, σ = {sigma:.0f} DPS, γ = {rotation_obj.rotation_skewness:.3f}",
        xaxis_title="Damage per second (DPS)",
        yaxis_title="Frequency",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=0.97, xanchor="center", x=0.5),
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
            style_header={"backgroundColor": "rgb(48, 48, 48)", "color": "white"},
            style_data={"backgroundColor": "rgb(50, 50, 50)", "color": "white"},
        )
    ]
    return rotation_percentile_table


def how_tall_should_the_action_box_plot_be(n_actions:int):
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
    rotation_data, action_dps, active_dps_time, analysis_time
):
    """
    Show DPS distributions for actions as a collection of box and whisker plots.
    """
    t_div = active_dps_time / analysis_time

    n_actions = len(rotation_data.unique_actions_distribution)
    l_fence = np.zeros(shape=(n_actions))
    q1 = np.zeros(shape=(n_actions))
    q2 = np.zeros(shape=(n_actions))
    q3 = np.zeros(shape=(n_actions))
    u_fence = np.zeros(shape=(n_actions))
    uu_fence = np.zeros(shape=(n_actions)) # 99th %
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
            marker=dict(size=9, color="#FFA15A"),
            customdata=custom_data,
            hovertemplate=hovertemplate_text,
        )
    )

    fig.update_yaxes(labelalias=ytick_labels, dtick=1, range=[-0.5, n_actions - 0.5])
    fig.update_xaxes(title="Damage per second (DPS)")

    # Title and place the legend at the top
    # Horizonal space much more constrained than vertical.
    fig.update_layout(
        title="DPS distributions by action",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


def make_action_pdfs_figure(rotation_obj, action_dps, active_dps_time, analysis_time):
    """
    Plot damage distributions for each action.
    The actual damage dealt is also plotted.

    Inputs:
    rotation_obj - Rotation object from ffxiv_stats with damage distributions computed.
    action_dps - pd DataFrame with columns "ability_name" and "amount"

    Returns:
    Plotly figure with action DPS distributions plotted
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


def make_action_table(rotation_obj, action_df):
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
        action_df,
        rotation_obj.unique_actions_distribution,
        rotation_obj.active_dps_t,
        rotation_obj.analysis_t,
    ).sort_values("actual_dps_dealt", ascending=False)
    action_summary_df = action_summary_df.rename(
        columns={
            "ability_name": "Action",
            "dps_50th_percentile": "DPS 50th %",
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
            id="DPS 50th %",
            name="DPS 50th %",
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
            style_header={"backgroundColor": "rgb(48, 48, 48)", "color": "white"},
            style_data={"backgroundColor": "rgb(50, 50, 50)", "color": "white"},
        )
    ]
    return action_summary_table


def make_kill_time_graph(party_rotation_dataclass, kill_time_seconds: int):
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
        "<b>Kill time: %{x}</b><br><br>"
        "% of kills faster than %{x}: %{y}"
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


def make_party_rotation_pdf_figure(party_analysis_data):
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
                marker={"size": 14, "color": "#FFA15A"},
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
