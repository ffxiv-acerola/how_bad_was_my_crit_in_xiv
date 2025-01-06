from typing import Union

import dash_bootstrap_components as dbc
from dash import html


def error_alert(error_string: Union[str, html.P]) -> dbc.Alert:
    """Create a Bootstrap alert component for displaying errors.

    Args:
        error_string: Error message to display. Can be string or html.P component

    Returns:
        dbc.Alert: Styled error alert component

    Example:
        >>> error_alert("Failed to load data")
        >>> error_alert(html.P("Database connection error"))
    """
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
