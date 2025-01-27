import dash
import dash_auth
import dash_bootstrap_components as dbc
from dash import html

from crit_app.config import DASH_AUTH_SECRET, ERROR_LOGIN_DATA
from crit_app.pages import errors

# Create a separate Dash instance just for the errors page
errors_app = dash.Dash(
    __name__,
    url_base_pathname="/errors/",
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
        dbc.icons.FONT_AWESOME,
    ],
)
error_server = errors_app.server

# Set the secret key for the Flask server
errors_app.server.secret_key = DASH_AUTH_SECRET

# Protect this entire app with BasicAuth
auth = dash_auth.BasicAuth(errors_app, ERROR_LOGIN_DATA, secret_key=DASH_AUTH_SECRET)

# Use the layout from errors.py
errors_app.layout = dbc.Container(
    [html.H1("Error dashboard"), html.Hr(), errors.layout()], fluid="md"
)

if __name__ == "__main__":
    errors_app.run(debug=True, port="8051")
