import dash
from dash import html

from crit_app.pages.math import math_layout

dash.register_page(
    __name__,
    path="/about",
)

about_layout = html.Div(
    [
        html.H2("About howbadwasmycritinxiv.com"),
        html.H3("Does this account for..."),
        html.P(
            "In most cases, yes. Damage variance due to different hit "
            "types (normal, critical, direct, and critical-direct) are "
            "accounted for along with the ±5% damage roll. Even the small "
            "gaps in the damage support due to integer math are accounted "
            "for. Rotational variance, like Minor Arcana or action procs "
            "are not accounted for because they cannot be reliably "
            "inferred from a log. This site only analyzes what is "
            "reported FFLogs and does not attempt to make any rotational "
            "inferences."
        ),
        html.P(
            "Most aspects of the battle system are also accounted for, "
            "including potency falloff from multi-hit damage, "
            "damage buffs, hit type buffs (including how they "
            "interact with guaranteed hit types, i.e. Chain Stratagem + "
            "Midare Setsugekka), and pet potency."
        ),
        html.H3("Why do I need to enter a job build?"),
        html.P(
            "Your job build is needed to compute how much damage each "
            "action does before any sort of damage variability as well "
            "as your critical hit rate and direct hit rate to accurately "
            "model damage variability. ACT and FFLogs is unable to "
            "reliably gather this information, so it must be explicitly "
            "specified."
        ),
        html.H3("Is there an example with everything already filled out?"),
        html.A(
            "Right here.",
            href="https://howbadwasmycritinxiv.com/analysis/"
            "3d009fc6-5198-4bca-97df-a156c67fb908",
        ),
        html.H3("Who is this site for?"),
        html.P(
            [
                "This sort of analysis is most helpful to people who "
                "have a rotation/kill time largely planned out and wish "
                "to see damage varied from run-to-run, or how likely a "
                "higher-DPS run is and by how much DPS. This site will "
                "not tell you how to improve your rotation - a site like ",
                html.A(
                    "xivanalysis",
                    href="https://xivanalysis.com/",
                    target="_blank",
                ),
                " is better-suited for that. In general, being able to "
                "perform a better rotation will have a much larger impact "
                "on damage dealt than good crit RNG.",
            ]
        ),
        html.H3("How are damage distributions calculated (short)?"),
        html.P("Lots of convolutions."),
        html.H3("How are damage distributions calculated (longer)?"),
        math_layout,
    ]
)


def layout():
    return about_layout
