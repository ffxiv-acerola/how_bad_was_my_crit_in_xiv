import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from crit_app.config import DEBUG

app = dash.Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True, # needed because some callbacks use dynamically generated id's
)

app.title = "How bad was my crit in FFXIV?"
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
            "This website is still in its early stages of development, so expect some sharp edges. Only fights from Anabeiseos are currently supported. Only Sage, Scholar, and White Mage are currently supported. Runs with duplicate healers will currently likely not behave as intended. If you have any suggestions, come across bugs, or would like to contribute, you can contact me on Discord at @cherryjesus."
        ),
        html.A("More about this site", href="#", id="about-open"),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(html.H2("About this site"))),
                dbc.ModalBody(
                    [
                        html.H2("How are damage distributions calculated?"),
                        html.P(
                            [
                                "Damage distributions are exactly computed by taking the damage distribution for an action landing a single hit - a ",
                                html.A("mixture distribution", href="https://en.wikipedia.org/wiki/Mixture_distribution", target="_blank"),
                                " weighted by likelihood of each hit type. The 1-hit action distribution is convolved with itself, ", 
                               html.A("which corresponds to a sum of random variables", href="https://en.wikipedia.org/wiki/Convolution_of_probability_distributions", target="_blank"),
                               ", to yield an n-hit damage distribution. The theory behind computing damage distributions is discussed more detail ",
                               html.A("here", href="https://github.com/ffxiv-acerola/damage_variability_papers/blob/main/01_variability_in_damage_calculations/Variability%20in%20damage%20calculations.pdf", target="_blank"),
                                " and ",
                               html.A("here", href="https://github.com/ffxiv-acerola/damage_variability_papers/blob/main/02_damage_distributions_deterministic_stochastic/Damage%20distributions%20for%20deterministic%20and%20stochastic%20rotations.pdf", target="_blank"),
                               ". Note that damage distributions are exact and there is no sampling error."
                            ]     
                        ),
                        html.H2("Why do I need to enter a job build?"),
                        html.P("Your job build is needed to compute how much damage each action does before any sort of damage variability as well as your critical hit rate and direct hit rate to accurately model damage variability. ACT and FFLogs is unable to reliably gather this information, so it must be explicitly specified."),
                        html.H2("Where is AST?"),
                        html.P("The buff effect of Astrodyne depends on the number of unique seals and the chance of getting 1, 2, or 3 unique seals depends on the specific Card Draw/Redraw used, which cannot be inferred from FFLogs. The random Haste buff from Harmony of Body is also difficult to accurately model. Since AST is pending a rework in Dawntrail, it is unsupported."),
                        html.H2("Who is this site for?"),
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


if __name__ == "__main__":
    app.run(debug=DEBUG)
