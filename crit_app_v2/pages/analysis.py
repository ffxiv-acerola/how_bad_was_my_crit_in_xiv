"""Player-analysis job-stats workbench."""

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, no_update

from crit_app_v2.build_providers import (
    BuildProvider,
    BuildProviderError,
    LoadedXivGearBuild,
    validate_job_stats_form,
)
from crit_app_v2.build_providers.build_dispatch import (
    load_job_build,
    validate_job_build_url,
)
from crit_app_v2.fflogs_encounters.encounters import fetch_encounter
from crit_app_v2.fflogs_encounters.errors import FFLogsError
from crit_app_v2.fflogs_encounters.models import Encounter
from crit_app_v2.game_data import (
    ROLE_SPECS,
    SPEED_STAT_SPEC,
    Role,
    Stats,
)
from crit_app_v2.ui.build_errors import build_error_message
from crit_app_v2.ui.fflogs_encounter import (
    encounter_title,
    encounter_to_store,
    fflogs_encounter_card,
    job_selection,
    phase_select_state,
)
from crit_app_v2.ui.fflogs_errors import fflogs_error_message
from crit_app_v2.ui.job_stats import player_analysis_job_build

dash.register_page(__name__, path="/analysis")


def layout():
    """Render the initial player-analysis job-stats form."""
    return dmc.Container(
        [
            player_analysis_job_build(
                # "hello",
                # Role("Tank"),
                # 4000,
                # 800,
                # 3000,
                # 500,
                # 3000,
                # 2000,
                # 190,
            ),
            dmc.Space(),
            fflogs_encounter_card(),
        ],
        size="xl",
        py="xl",
    )


@callback(
    Output("main-stat-input", "label"),
    Output("speed-stat-input", "label"),
    Output("bottom-build-row", "style"),
    Input("role-select", "value"),
)
def role_stat_labels(selected_role: Role):
    """Return role-specific main/speed labels and Tenacity visibility."""
    role = Role(selected_role)
    role_spec = ROLE_SPECS[role]
    style = {"display": "block" if role_spec.requires_tenacity else "none"}
    return (
        role_spec.main_stat_label,
        SPEED_STAT_SPEC[role_spec.speed_stat].display_name,
        style,
    )


def _xiv_gear_selector_state(build: LoadedXivGearBuild):
    """Return selector options, visibility, and selected response index."""
    options = [
        {"label": set_.build_name, "value": str(set_.response_index)}
        for set_ in build.sets
    ]
    selected_index = build.build_index
    if selected_index is None and len(build.sets) == 1:
        selected_index = build.sets[0].response_index

    selected_value = str(selected_index) if selected_index is not None else None
    style = {} if len(options) > 1 else {"display": "none"}
    return options, style, selected_value


@callback(
    Output("loaded-job-build", "data"),
    Output("gearset-url", "error"),
    Output("xiv-gear-select", "data"),
    Output("xiv-gear-select", "style"),
    Output("xiv-gear-select", "value"),
    Input("gearset-url-button", "n_clicks"),
    State("gearset-url", "value"),
    prevent_initial_call=True,
)
def load_job_build_from_url(n_clicks: int | None, raw_url: str | None):
    """Load a provider build and prepare any XIVGear sheet choices."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    if not raw_url or not raw_url.strip():
        return None, "Enter a gearset URL.", [], {"display": "none"}, None

    try:
        build_url = validate_job_build_url(raw_url)
        loaded_build = load_job_build(build_url)
    except BuildProviderError as error:
        return (
            None,
            build_error_message(error),
            [],
            {"display": "none"},
            None,
        )

    if isinstance(loaded_build, LoadedXivGearBuild):
        selector_data, selector_style, selector_value = _xiv_gear_selector_state(
            loaded_build
        )
    else:
        selector_data, selector_style, selector_value = [], {"display": "none"}, None

    return (
        loaded_build.model_dump(mode="json"),
        None,
        selector_data,
        selector_style,
        selector_value,
    )


@callback(
    Output("role-select", "value"),
    Output("main-stat-input", "value"),
    Output("determination-stat-input", "value"),
    Output("speed-stat-input", "value"),
    Output("critical-hit-stat-input", "value"),
    Output("direct-hit-stat-input", "value"),
    Output("weapon-damage-stat-input", "value"),
    Output("tenacity-stat-input", "value"),
    Input("loaded-job-build", "data"),
    Input("xiv-gear-select", "value"),
)
def apply_loaded_job_build(build_data: dict | None, selected_index: str | None):
    """Populate the role and stat inputs from the loaded provider data."""
    unchanged = (no_update,) * 8
    if not build_data:
        return unchanged

    provider = build_data.get("build_provider")
    if provider == BuildProvider.XIV_GEAR:
        if selected_index is None:
            return unchanged
        try:
            response_index = int(selected_index)
        except (TypeError, ValueError):
            return unchanged

        selected_set = next(
            (
                set_data
                for set_data in build_data.get("sets", [])
                if set_data.get("response_index") == response_index
            ),
            None,
        )
        if selected_set is None:
            return unchanged
        stats = selected_set["build_stats"]
        role = build_data["build_role"]
    else:
        stats = build_data["build_stats"]
        role = build_data["build_role"]

    return (
        role,
        stats["main_stat"],
        stats["determination"],
        stats["speed_stat"],
        stats["critical_hit"],
        stats["direct_hit"],
        stats["weapon_damage"],
        stats["tenacity"],
    )


@callback(
    Output("fflogs-url-button", "disabled"),
    Output("main-stat-input", "error"),
    Output("determination-stat-input", "error"),
    Output("speed-stat-input", "error"),
    Output("critical-hit-stat-input", "error"),
    Output("direct-hit-stat-input", "error"),
    Output("weapon-damage-stat-input", "error"),
    Output("tenacity-stat-input", "error"),
    Input("role-select", "value"),
    Input("main-stat-input", "value"),
    Input("determination-stat-input", "value"),
    Input("speed-stat-input", "value"),
    Input("critical-hit-stat-input", "value"),
    Input("direct-hit-stat-input", "value"),
    Input("weapon-damage-stat-input", "value"),
    Input("tenacity-stat-input", "value"),
)
def job_build_validator(
    selected_role: Role,
    main_stat: int | None,
    determination: int | None,
    speed_stat: int | None,
    critical_hit: int | None,
    direct_hit: int | None,
    weapon_damage: int | None,
    tenacity: int | None,
):
    """Validate draft stats and map field errors to Dash callback outputs.

    The first returned value disables FFLogs submission while the form is
    incomplete or invalid; remaining values align with the stat error outputs.
    """
    stats = {
        Stats.MAIN_STAT: main_stat,
        Stats.DETERMINATION: determination,
        Stats.SPEED_STAT: speed_stat,
        Stats.CRITICAL_HIT: critical_hit,
        Stats.DIRECT_HIT: direct_hit,
        Stats.WEAPON_DAMAGE: weapon_damage,
        Stats.TENACITY: tenacity,
    }
    result = validate_job_stats_form(Role(selected_role), stats)
    return (
        not result.is_valid,
        result.errors[Stats.MAIN_STAT],
        result.errors[Stats.DETERMINATION],
        result.errors[Stats.SPEED_STAT],
        result.errors[Stats.CRITICAL_HIT],
        result.errors[Stats.DIRECT_HIT],
        result.errors[Stats.WEAPON_DAMAGE],
        result.errors[Stats.TENACITY],
    )


@callback(
    Output("loaded-encounter", "data"),
    Output("fflogs-url", "error"),
    Output("fflogs-url", "value"),
    Output("encounter-name-time", "children"),
    Output("phase-select", "data"),
    Output("phase-select", "value"),
    Output("phase-select", "style"),
    Output("job-selection", "children"),
    Input("fflogs-url-button", "n_clicks"),
    State("fflogs-url", "value"),
    State("role-select", "value"),
    prevent_initial_call=True,
)
def load_encounter_from_url(
    n_clicks: int | None, raw_url: str | None, selected_role: str
):
    """Fetch an FFLogs fight and populate the phase and job selectors."""
    if not n_clicks:
        return (no_update,) * 8

    reset_phase = ([{"value": "0", "label": "Entire Fight"}], "0", {"display": "none"})
    role = Role(selected_role)

    if not raw_url or not raw_url.strip():
        return (
            None,
            "Enter an FFLogs report URL.",
            no_update,
            "",
            *reset_phase,
            job_selection(None, role),
        )

    try:
        encounter = fetch_encounter(raw_url)
    except FFLogsError as error:
        return (
            None,
            fflogs_error_message(error),
            no_update,
            "",
            *reset_phase,
            job_selection(None, role),
        )

    return (
        encounter_to_store(encounter),
        None,
        str(encounter.encounter_url.build_url),
        encounter_title(encounter),
        *phase_select_state(encounter),
        job_selection(encounter, role),
    )


@callback(
    Output("job-selection", "children", allow_duplicate=True),
    Input("role-select", "value"),
    State("loaded-encounter", "data"),
    State("player-select", "value"),
    prevent_initial_call=True,
)
def restrict_players_to_role(
    selected_role: str, encounter_data: dict | None, selected_player: str | None
):
    """Enable only players in the selected role, clearing a mismatched choice."""
    if not encounter_data:
        return no_update
    encounter = Encounter.model_validate(encounter_data)
    return job_selection(encounter, Role(selected_role), selected_player)
