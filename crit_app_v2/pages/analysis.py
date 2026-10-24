"""Player-analysis job-stats workbench."""

import dash
import dash_mantine_components as dmc

from crit_app_v2.ui.job_stats import player_analysis_job_build

dash.register_page(__name__, path="/analysis")


def layout():
    """Render the initial player-analysis job-stats form."""
    return dmc.Container(
        player_analysis_job_build(),
        size="xl",
        py="xl",
    )
