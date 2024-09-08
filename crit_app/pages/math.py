# fmt: off
import sys
# I hate pythonpath i hate pythonpath i hate pythonpath i hate pythonpath
sys.path.append("../../") 
# fmt: on


import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd


dash.register_page(
    __name__,
    path="/math",
)

one_hit_df = pd.read_parquet(
    "crit_app/math_data/1-hit.parquet"
)

two_hit_df = pd.read_parquet(
    "crit_app/math_data/2-hit.parquet"
)

five_hit_df = pd.read_parquet(
    "crit_app/math_data/5-hit.parquet"
)

ten_hit_df = pd.read_parquet(
    "crit_app/math_data/10-hit.parquet"
)

fifteen_hit_df = pd.read_parquet(
    "crit_app/math_data/15-hit.parquet"
)

one_hit_dmg_df = pd.read_parquet(
    "crit_app/math_data/1-hit-dmg.parquet"
)

one_hit_crit_df = pd.read_parquet(
    "crit_app/math_data/1-hit-crit.parquet"
)

green = "#009670"

one_hit_fig = px.line(
    data_frame=one_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    color_discrete_sequence=[green],
)

two_hit_fig = px.line(
    data_frame=two_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="2-Hit damage distribution",
    color_discrete_sequence=[green],
)

five_hit_fig = px.line(
    data_frame=five_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="5-Hit damage distribution",
    color_discrete_sequence=[green],
)

ten_hit_fig = px.line(
    data_frame=ten_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="10-Hit damage distribution",
    color_discrete_sequence=[green],
)

fifteen_hit_fig = px.line(
    data_frame=fifteen_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="15-Hit damage distribution",
    color_discrete_sequence=[green],
)

one_hit_none_fig = px.line(
    data_frame=one_hit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="No buffs",
    height=300,
    range_x=[950, 2300],
    range_y=[0, 0.5],
    color_discrete_sequence=[green],
)

one_hit_dmg_fig = px.line(
    data_frame=one_hit_dmg_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="8% Damage buff",
    height=300,
    range_x=[950, 2300],
    range_y=[0, 0.5],
    color_discrete_sequence=[green],
)

one_hit_crit_fig = px.line(
    data_frame=one_hit_crit_df,
    x="x",
    y="y",
    template="plotly_dark",
    labels={"x": "Damage dealt", "y": "Probability"},
    title="10% Critical hit rate buff",
    height=300,
    range_x=[950, 2300],
    range_y=[0, 0.5],
    color_discrete_sequence=[green],
)

rotation_df = pd.read_json(
    "crit_app/math_data/rotation_df.json"
).rename(
    columns={
        "action_name": "Action",
        "base_action": "Base action",
        "l_c": "Critical damage mult.",
        "damage_type": "Damage Type",
    }
).sort_values(["Base action", "n"], ascending=[True, False])
rotation_df[["p_n", "p_c", "p_d", "p_cd"]] = rotation_df[["p_n", "p_c", "p_d", "p_cd"]].round(3)


math_layout = html.Div(
    [
        dcc.Markdown(
            r"""
## How are damage distributions computed?

This page briefly describes how damage/DPS distributions are exactly computed. This page works in units of total damage dealt since that is the natural system of units to work in. Converting to DPS simply requires dividing damage by the time elapsed.

For more detailed discussion of computing damage distributions, please refer to [this repository.](https://github.com/ffxiv-acerola/damage_variability_papers/tree/main)

Damage distributions are computed using the `ffxiv_stats` [Python package](https://github.com/ffxiv-acerola/ffxiv_stats).

### Sources of damage variability

There are two main sources of damage variability in FFXIV, hit types and a $\pm 5\%$ damage roll centered around a base damage value, $D_2$ - this is the same $D_2$ value from "How to be a Math Wizard, Volume 3" after potency has been converted into damage but before any damage variability is introduced. There are four different possible hit types, normal ($n$), critical ($c$), direct ($d$) and critical-direct ($cd$). The damage for each of these hit types are

$$
\begin{align}
D_n &= D_2 \nonumber \\
D_c &= \lfloor \lfloor D_2 \lambda_c \rfloor/ 1000 \rfloor \nonumber \\
D_d &= \lfloor \lfloor 125 D_2 \rfloor/ 100 \rfloor \nonumber \\
D_{cd} &= \lfloor \lfloor 125\lfloor D_2 \lambda_c \rfloor/ 1000 \rfloor / 100 \rfloor \nonumber \\
\end{align}
$$

where $\lfloor \cdot \rfloor$ is the floor operator and $\lambda_c$ is the multiplier for critical damage. After the hit type is determined, a $\pm 5\%$ damage roll and buffs are applied, resulting in an approximately discrete uniform distribution for hit type $i$,

$$
P(D_i) = \left \lfloor \mathcal{U}\{ \lfloor 0.95 D_i \rfloor, \lfloor 1.05 D_i \rfloor \} b_i \right \rfloor,
$$

where $\mathcal{U}\{A, B\}$ denotes a discrete uniform distribution from $A$ to $B$ and $b_i$ is total damage multiplier of all buffs present. The distribution is only approximately uniform because buffs and flooring operations can cause gaps in the damage support. For DoT effects buffs the damage roll is applied before the hit type is determined.

The chance for landing each type of hit, $w_i$ is

$$
\begin{align}
w_n &= 1 - p_c - p_d + p_c p_d \nonumber \\
w_c &= p_c - p_{c} p_d \nonumber \\
w_d &= p_d - p_{c} p_d \nonumber \\
w_{cd} &= p_c p_d \nonumber \\
\end{align}
$$

Here, $p_c$ and $p_d$ represent the critical hit rate and direct hit rate associated with the critical hit stat and direct hit rate stat, respectively. Because critical-direct hits are possible, the probability of those hits must be subtracted out of critical and direct hits so they are not double counted. The variables $w_c$ and $w_d$ are formally defined as the chance of landing a critical or direct hit, given a critical-direct hit does not occur.

### The one-hit and $n$-hit damage distribution

The above equations allows us to exactly write down the probability distribution for an action landing a single hit as a mixture distribution

$$
P(D; n=1) = w_n P(D_n) + w_c P(D_c) + w_d P(D_d) + w_{cd} P(D_{cd}).
$$

An example of a one-hit distribution is shown below, $D_2 = 1000$, $w_n = 0.497187$, $w_c = 0.184822$, $w_d = 0.231822$, and $w_{cd} = 0.086178$.
""",
            mathjax=True,
        ),
        dcc.Graph(figure=one_hit_fig),
        dcc.Markdown(
            r"""
The plateaus represent normal, direct, critical, and critical-direct hits from left to right.

Most encounters involve an action being used more than once, so we need a way to compute an $n$-hit damage distribution. The damage dealt in a one-hit damage distribution is randomly distributed, so convolving $P(D; n=1)$ with itself corresponds to a sum of random variables, i.e., a 2-hit distribution. In general, an action landing $n_h$ hits can be computed by convolving the 1-hit damage distribution with itself $n_h - 1$ times,

$$
P(D;n_h) = \underbrace{P(D; n = 1) \ast P(D; n = 1) \ast\dots\ast P(D; n = 1)}_{n_h}.
$$

Here, the $\ast$ operator denotes a convolution. This process is conceptually the same as rolling multiple dice together and summing their values. Here, the probability distributions are just more complicated than those od dice. Because the one-hit damage distribution is non-trivial, $n$-hit damage distributions are numerically computed using Fast Fourier Transforms.

The figure below shows the 2-, 5-, 10-, and 15-hit damage distributions, derived from the one-hit damage distribution shown above.
""",
            mathjax=True,
        ),
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=two_hit_fig), width=12, md=6),
                        dbc.Col(dcc.Graph(figure=five_hit_fig), width=12, md=6),
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=ten_hit_fig), width=12, md=6),
                        dbc.Col(dcc.Graph(figure=fifteen_hit_fig), width=12, md=6),
                    ],
                ),
            ],
        ),
        dcc.Markdown(
            r"""
As the number of hits increase, the damage distribution more closely resembles a normal distribution.

### Defining and counting actions

From the above section, what exactly is considered an action and how they should be counted is specifically defined; an "action" is considered unique if its one-hit damage distribution is unique. Damage buffs, hit type buffs, medication, and guaranteed hit types all change the one-hit damage distribution and must counted separately.

For example, Glare III, Glare III with Chain Stratagem, Glare III with Arcane Circle, and Glare III with Arcane Circle and Chain Stratagem all have different one-hit damage distributions, and would be separately counted. This is also how all the various buffs are accounted for. The figure below shows the same 1-hit damage distribution with no buffs, an 8% damage buff, and a 10% critical hit rate buff.

""",
            mathjax=True,
        ),
        dbc.Row(dcc.Graph(figure=one_hit_none_fig)),
        dbc.Row(dcc.Graph(figure=one_hit_dmg_fig)),
        dbc.Row(dcc.Graph(figure=one_hit_crit_fig)),
        dcc.Markdown(
            r"""
    Note how the damage buff shifts the one-hit distribution further right and a critical hit rate buff increases the height of the third and fourth plateau.

    ## Computing rotation damage distributions

    A rotation is defined a collection of actions, along with their number of hits, hit type probabilities, base damage, critical hit strength, and total buff strength. Due to the combinatorics of buff combinations, a realistic rotation often consist of many actions. The rotation damage distribution can be computed in the same way as we computed our $n$-hit damage distribution for an action: convolve all the action damage distributions together.

    The table below shows a realistic White Mage rotation from an actual encounter in-game.
    """,
            mathjax=True,
        ),
        dbc.Table.from_dataframe(rotation_df, striped=True, bordered=True, hover=True),
    ],
)


def layout():
    return math_layout
