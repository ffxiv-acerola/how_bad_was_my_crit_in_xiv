"""
Example of creating a custom 404 page to display when the URL isn't found
"""


from dash import html, register_page
import dash_bootstrap_components as dbc

register_page(__name__, path="/404")


body = html.Div(
    [
        html.H2("404 Not Found"),
        html.P(
            [
                "The link entered does not exist. ",
                html.A("Click here", href="/"),
                " to return home and analyze a rotation."
            ]
        )
    ]
)

layout = dbc.Container(
    [
        body
    ],
    fluid="md",
)