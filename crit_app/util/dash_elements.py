
from dash import html
import dash_bootstrap_components as dbc

def error_alert(error_string):
    return dbc.Alert(
        [
            html.P(
                "Oops, the following error was encountered while creating and analyzing your rotation:"
            ),
            error_string,
            html.P(
                "This error has been logged and will be fixed when possible. No further action is required."
            ),
        ],
        color="danger",
    )