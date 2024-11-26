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
    # external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=not DEBUG,  # needed because some callbacks use dynamically generated id's
)

app.title = "How bad was my crit in FFXIV?"
app.name = "Player analysis"
app._favicon = "crit_app/assets/favicon.ico"
server = app.server

###################################################
### Defining most of the layout/static elements ###
###################################################

header = html.Div(
    [
        dcc.Store(id="store"),
        html.H1("How bad was my crit in FFXIV?"),
        html.P(
            "Have you ever wondered how (un)lucky your critical/direct hit rate and corresponding DPS for a run was? Maybe you crit every action and want to know how likely a better run is and by how much DPS. Or maybe your crit was so bad you would like mathematical proof quantifying just how unlucky you are."
        ),
        html.P(
            "For a given run, howbadwasmycritinxiv pulls your rotation and how much damage each action did from FFLogs. Using your job build, it exactly simulates how likely all possible DPS values are due to damage variability and compares it to your actual DPS. To get started, all you need is your job build and link to a fight log."
        ),
        html.P(
            [
                "This site supports analysis from Anabeiseos, Dawntrail's EX2, AAC Light-Heavyweight, ",
                html.I("and now FRU!"), 
                " If you have any suggestions, come across bugs, or would like to contribute, join the ",
                html.A(
                    "Discord server",
                    href="https://discord.gg/8eezSgy3sC",
                    target="_blank",
                ),
                ".",
            ]
        ),
        html.P(
            [
                "Compute damage distributions for a party and estimate kill time ",
                html.A("here.", href="/party_analysis"),
            ]
        ),
        html.A("More about this site", href="#", id="about-open"),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(html.H2("About this site"))),
                dbc.ModalBody(
                    [
                        html.H3("How are damage distributions calculated?"),
                        html.P("The short answer: lots of convolutions."),
                        html.P(
                            [
                                "The long answer: check out ",
                                html.A("this page", href="/math", target="_blank"),
                                " for a more detailed explanation.",
                            ]
                        ),
                        html.H3("Does this account for..."),
                        html.P(
                            r"In most cases, yes. Damage variance due to different hit types (normal, critical, direct, and critical-direct) are accounted for along with the ±5% damage roll. Even the small gaps in the damage support due to integer math are accounted for. Rotational variance, like Minor Arcana or action procs are not accounted for because they cannot be reliably inferred from a log. This site only analyzes what is reported FFLogs and does not attempt to make any rotational inferences."
                        ),
                        html.P(
                            "Most aspects of the battle system are also accounted for, including damage buffs, hit type buffs (including how they interact with guaranteed hit types, i.e. Chain Stratagem + Midare Setsugekka), and pet potency."
                        ),
                        html.H3("Why do I need to enter a job build?"),
                        html.P(
                            "Your job build is needed to compute how much damage each action does before any sort of damage variability as well as your critical hit rate and direct hit rate to accurately model damage variability. ACT and FFLogs is unable to reliably gather this information, so it must be explicitly specified."
                        ),
                        html.H3(
                            "Is there an example with everything already filled out?"
                        ),
                        html.A(
                            "Right here.",
                            href="https://howbadwasmycritinxiv.com/analysis/3d009fc6-5198-4bca-97df-a156c67fb908",
                        ),
                        html.H3("Who is this site for?"),
                        html.P(
                            [
                                "This sort of analysis is most helpful to people who have a rotation/kill time largely planned out and wish to see damage varied from run-to-run, or how likely a higher-DPS run is and by how much DPS. This site will not tell you how to improve your rotation - a site like ",
                                html.A(
                                    "xivanalysis",
                                    href="https://xivanalysis.com/",
                                    target="_blank",
                                ),
                                " is better-suited for that. In general, being able to perform a better rotation will have a much larger impact on damage dealt than good crit RNG.",
                            ]
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    dbc.Button(
                        "Close", id="about-close", className="ms-auto", n_clicks=0
                    )
                ),
            ],
            id="about-modal",
            is_open=False,
            size="lg",
        ),
        html.Hr(),
    ]
)

# Putting it all together
app.layout = dbc.Container(
    [
        dcc.Location(id="url", refresh="callback-nav"),
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
    """
    Open/close the modal discussing the consequences of DPS vs rDPS/aDPS.
    """
    if n1 is None or n2 is None:
        raise PreventUpdate
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("about-modal", "is_open"),
    Input("about-open", "n_clicks"),
    Input("about-close", "n_clicks"),
    State("about-modal", "is_open"),
)
def toggle_about_modal(n1, n2, is_open):
    """
    Open/close the "about this site" modal.
    """
    if n1 is None or n2 is None:
        raise PreventUpdate
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("party-analysis-modal", "is_open"),
    Input("party-analysis-open", "n_clicks"),
    Input("party-analysis-close", "n_clicks"),
    State("party-analysis-modal", "is_open"),
)
def toggle_party_analysis_modal(n1, n2, is_open):
    """
    Open/close the "about this site" modal.
    """
    if n1 is None or n2 is None:
        raise PreventUpdate
    if n1 or n2:
        return not is_open
    return is_open


if __name__ == "__main__":
    app.run(debug=DEBUG)
