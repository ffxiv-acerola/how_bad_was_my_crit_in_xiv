"""Player-analysis job-stats workbench."""

import dash
import dash_mantine_components as dmc

from crit_app_v2.mantine_cards import initialize_job_build

dash.register_page(__name__, path="/analysis")


def layout():
    """Render the initial player-analysis job-stats form."""
    return dmc.Container(
        initialize_job_build(),
        size="xl",
        py="xl",
    )
