import dash
import dash_bootstrap_components as dbc
import diskcache
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from dash.long_callback import DiskcacheLongCallbackManager

from crit_app.config import DEBUG

cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
        dbc.icons.FONT_AWESOME,
    ],
    long_callback_manager=long_callback_manager,
    suppress_callback_exceptions=not DEBUG,  # needed because some callbacks use dynamically generated id's
)

app.title = "How bad was my crit in FFXIV?"
app.name = "Player analysis"
app._favicon = "crit_app/assets/favicon.ico"
server = app.server

nav = dbc.Nav(
    [
        dbc.NavItem(dbc.NavLink("Player Analysis", active="partial", href="/analysis")),
        dbc.NavItem(
            dbc.NavLink("Party Analysis", active="partial", href="/party_analysis")
        ),
        dbc.NavItem(dbc.NavLink("Analysis History", active="partial", href="/history")),
        dbc.DropdownMenu(
            [
                dbc.DropdownMenuItem(
                    dbc.NavLink(
                        "Supported fights", active="exact", href="/compatibility"
                    )
                ),
                dbc.DropdownMenuItem(
                    dbc.NavLink("FAQs", active="exact", href="/about")
                ),
            ],
            label="About",
            nav=True,
        ),
        dbc.NavItem(dbc.NavLink("Discord", href="https://discord.gg/8eezSgy3sC")),
    ],
    pills=True,
)
###################################################
### Defining most of the layout/static elements ###
###################################################

header = html.Div(
    [
        dcc.Store(id="store"),
        html.H1("How bad was my crit in FFXIV?"),
        html.P(
            "Have you ever wondered how (un)lucky your critical/direct hit rate and "
            "corresponding DPS for a run was? Maybe you crit every action and want to "
            "know how likely a better run is and by how much DPS. Or maybe your crit "
            "was so bad you would like mathematical proof quantifying just how unlucky you are."
        ),
        html.P(
            "For a given run, howbadwasmycritinxiv pulls your rotation and how much "
            "damage each action did from FFLogs. Using your gearset, it exactly "
            "simulates how likely all possible DPS values are due to damage variability "
            "and compares it to your actual DPS. To get started, all you need is your "
            "gearset and link to a fight log."
        ),
        html.Hr(),
        nav,
        html.Br(),
    ]
)

# Putting it all together
# Add a hidden div at the top of the layout for clientside callbacks to use
app.layout = dbc.Container(
    [
        # dcc.Location(id="url", refresh="callback-nav"),
        dcc.Location(id="url", refresh=True),
        dcc.Store(
            id="analysis-history", storage_type="local", data=[], clear_data=False
        ),
        dcc.Store(id="saved-gearsets", storage_type="local", data=[], clear_data=False),
        dcc.Store(
            id="default-gear-index", storage_type="local", data=None, clear_data=False
        ),
        dcc.Store(id="analysis-indicator", storage_type="session", data=None),
        # Add this hidden div for clientside callbacks
        html.Div(id="_dummy_output", style={"display": "none"}),
        header,
        dash.page_container,
    ],
    fluid="md",
)


@app.callback(
    Output("result-interpretation-modal", "is_open"),
    Input("result-interpretation-open", "n_clicks"),
    Input("result-interpretation-close", "n_clicks"),
    State("result-interpretation-modal", "is_open"),
)
def toggle_interpretation_modal(n1, n2, is_open):
    """Open/close the modal discussing the consequences of DPS vs rDPS/aDPS."""
    if n1 is None or n2 is None:
        raise PreventUpdate
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(Output("url", "pathname"), Input("url", "pathname"))
def redirect_to_analysis(pathname: str) -> str:
    """Redirect root URL to analysis page."""
    if pathname == "/":
        return "/analysis"
    raise PreventUpdate


@app.callback(
    Output("party-analysis-modal", "is_open"),
    Input("party-analysis-open", "n_clicks"),
    Input("party-analysis-close", "n_clicks"),
    State("party-analysis-modal", "is_open"),
)
def toggle_party_analysis_modal(n1, n2, is_open):
    """Open/close the "about this site" modal."""
    if n1 is None or n2 is None:
        raise PreventUpdate
    if n1 or n2:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run(debug=DEBUG)
