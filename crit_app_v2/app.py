"""Application entry point for the next-generation DMC interface."""

from pathlib import Path

import dash
import dash_mantine_components as dmc
from dash import Input, Output, dcc
from dash.exceptions import PreventUpdate

from crit_app_v2.config import DEBUG

PAGES_FOLDER = Path(__file__).parent / "pages"

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=str(PAGES_FOLDER),
)

app.title = "How bad was my crit in FFXIV?"
server = app.server

app.layout = dmc.MantineProvider(
    dmc.Box(
        [
            dcc.Location(id="url", refresh=True),
            dash.page_container,
        ]
    ),
    forceColorScheme="dark",
)


@app.callback(
    Output("url", "pathname"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def redirect_to_analysis(pathname: str) -> str:
    """Redirect the application root to the player-analysis page."""
    if pathname == "/":
        return "/analysis"
    raise PreventUpdate


if __name__ == "__main__":
    app.run(debug=DEBUG)
