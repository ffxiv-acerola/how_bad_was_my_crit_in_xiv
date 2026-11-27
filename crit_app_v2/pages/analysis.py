"""Player-analysis job-stats workbench."""

import datetime
import traceback
from typing import Any
from uuid import uuid4

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
from pydantic import AnyHttpUrl, ValidationError

from crit_app_v2.analysis.dps_distribution import (
    PlayerDpsDistribution,
    get_dps_percentile,
)
from crit_app_v2.analysis.models import PlayerAnalysisStats, PreparedPlayerAnalysis
from crit_app_v2.analysis.player_analysis import (
    DISCRETIZATION_LEVEL_MAP,
    compute_party_bonus,
    correct_final_phase,
)
from crit_app_v2.analysis.rotation_analysis import rotation_analysis
from crit_app_v2.analysis.rotation_table import build_rotation_table
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

# Imported for its callback registrations.
from crit_app_v2.callbacks import gearsets as _gearset_callbacks  # noqa: F401
from crit_app_v2.db.access import PlayerAnalysisAccess, update_access_table
from crit_app_v2.db.analysis_blobs import save_player_analysis_blobs
from crit_app_v2.db.encounter import load_encounter, save_encounter
from crit_app_v2.db.errors import (
    PlayerAnalysisErrorRecord,
    insert_error_player_analysis,
)
from crit_app_v2.db.player_analysis import (
    PlayerAnalysisCreationRecord,
    PlayerAnalysisRecord,
    search_prior_player_analyses,
    update_player_analysis_creation_table,
    update_report_table,
)
from crit_app_v2.fflogs_encounters.encounters import fetch_encounter
from crit_app_v2.fflogs_encounters.errors import FFLogsError
from crit_app_v2.fflogs_encounters.models import Encounter, EncounterUrl
from crit_app_v2.game_data import (
    JOB_SPECS,
    ROLE_SPECS,
    SPEED_STAT_SPEC,
    Role,
    Stats,
)
from crit_app_v2.game_data.encounters import (
    get_encounter_spec,
    get_phase_options,
    is_player_analyzeable,
)
from crit_app_v2.ui.build_errors import build_error_message
from crit_app_v2.ui.fflogs_encounter import (
    encounter_title,
    encounter_to_store,
    fflogs_encounter_card,
    job_selection,
    phase_select_state,
    unsupported_encounter_message,
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
def apply_loaded_job_build(
    build_data: dict[str, Any] | None, selected_index: str | None
):
    """Populate the role and stat inputs from the loaded provider data."""
    unchanged = (no_update,) * 8
    if not build_data:
        return unchanged

    provider = build_data.get("build_provider")
    if provider == BuildProvider.INTERNAL:
        # A hidden XIVGear selector must not re-apply a saved gearset.
        if "loaded-job-build.data" not in ctx.triggered_prop_ids:
            return unchanged
        stats = build_data["build_stats"]
        role = build_data["build_role"]
    elif provider == BuildProvider.XIV_GEAR:
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

    if not is_player_analyzeable(encounter.encounter_id):
        return (
            None,
            unsupported_encounter_message(encounter),
            no_update,
            "",
            *reset_phase,
            job_selection(None, role),
        )

    save_encounter(encounter)

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
    selected_role: str,
    encounter_data: dict[str, Any] | None,
    selected_player: str | None,
):
    """Enable only players in the selected role, clearing a mismatched choice."""
    if not encounter_data:
        return no_update
    encounter = Encounter.model_validate(encounter_data)
    return job_selection(encounter, Role(selected_role), selected_player)


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("player-analysis-feedback", "children"),
    Input("player-analyze-button", "n_clicks"),
    State("role-select", "value"),
    State("main-stat-input", "value"),
    State("determination-stat-input", "value"),
    State("speed-stat-input", "value"),
    State("critical-hit-stat-input", "value"),
    State("direct-hit-stat-input", "value"),
    State("weapon-damage-stat-input", "value"),
    State("tenacity-stat-input", "value"),
    State("loaded-encounter", "data"),
    State("fflogs-url", "value"),
    State("phase-select", "value"),
    State("player-select", "value"),
    prevent_initial_call=True,
)
def analyze_and_register_rotation(
    n_clicks: int | None,
    selected_role: str,
    main_stat_pre_bonus: int | None,
    determination: int | None,
    speed_stat: int | None,
    critical_hit: int | None,
    direct_hit: int | None,
    weapon_damage: int | None,
    tenacity: int | None,
    encounter_data: dict[str, Any] | None,
    raw_fflogs_url: str | None,
    selected_phase: str | list[str] | None,
    selected_player_id: str | None,
) -> tuple[Any, str]:
    """Validate player-analysis inputs and resolve prior analyses.

    This callback intentionally stops immediately before rotation analysis;
    rotation construction and its error handling remain a separate step.
    """

    # Very long pre-flight check server-side

    # Things are selected
    if n_clicks is None:
        raise PreventUpdate
    if not selected_player_id:
        return no_update, "No player selected."
    if not encounter_data or not raw_fflogs_url or not raw_fflogs_url.strip():
        return no_update, "Please submit an FFLogs URL and select a player."

    # Check that the encounter data stored client side still validates
    try:
        stored_encounter = Encounter.model_validate(encounter_data)
        input_url = EncounterUrl(build_url=AnyHttpUrl(raw_fflogs_url.strip()))
    except (ValidationError, ValueError, TypeError):
        return no_update, "Please resubmit the FFLogs URL; the encounter changed."

    # A successful load replaces fight=last with the resolved numeric ID.
    # Any later URL edit may leave the selectors stale, so require a resubmit.
    stored_url_fight = stored_encounter.encounter_url.fight_id
    if (
        not isinstance(stored_url_fight, int)
        or stored_url_fight != stored_encounter.fight_id_resolved
        or input_url.report_id != stored_encounter.encounter_url.report_id
        or input_url.fight_id != stored_encounter.fight_id_resolved
    ):
        return no_update, "Please resubmit the FFLogs URL; the encounter changed."

    # At this point all of the client-side data is likely unchanged
    # and is valid encounter information which should have been saved to the DB.
    # Try to load the encounter information from DB once everything checks out
    try:
        encounter = load_encounter(
            stored_encounter.encounter_url.report_id,
            stored_encounter.fight_id_resolved,
        )
    except (ValidationError, ValueError):
        return (
            no_update,
            "Please resubmit the FFLogs URL; the encounter is unavailable.",
        )

    if encounter is None or not is_player_analyzeable(encounter.encounter_id):
        return (
            no_update,
            "Please resubmit the FFLogs URL; the encounter is unavailable.",
        )

    # Validate player selection
    try:
        player_id = int(selected_player_id)
        role = Role(selected_role)
    except (ValueError, TypeError):
        return no_update, "Please select a player in the selected role."

    player = next(
        (person for person in encounter.players if person.player_id == player_id), None
    )
    if player is None or player.role is not role:
        return no_update, "Please select a player in the selected role."

    if isinstance(selected_phase, list):
        selected_phase = selected_phase[0] if selected_phase else None
    try:
        phase_id = int(selected_phase) if selected_phase is not None else 0
    except (TypeError, ValueError):
        return no_update, "Select a valid fight phase."

    # Ensure phase information is correct
    if phase_id < 0:
        return no_update, "Select a valid fight phase."
    phase_id = correct_final_phase(phase_id, encounter.last_phase_index)
    allowed_phases = {
        option.value
        for option in get_phase_options(
            encounter.encounter_id, encounter.last_phase_index
        )
    }
    if phase_id not in allowed_phases:
        return no_update, "Select a valid fight phase."

    # Server-side validation on the job build stats
    try:
        stats = PlayerAnalysisStats.model_validate(
            {
                "job": player.job,
                "build": {
                    "role": role,
                    "stats": {
                        "main_stat": main_stat_pre_bonus,
                        "determination": determination,
                        "speed_stat": speed_stat,
                        "critical_hit": critical_hit,
                        "direct_hit": direct_hit,
                        "weapon_damage": weapon_damage,
                        "tenacity": tenacity if role is Role.TANK else None,
                    },
                },
                "party_bonus": compute_party_bonus(encounter),
            }
        )
    except ValidationError:
        return (
            no_update,
            "The selected role and job stats are invalid. Review the build.",
        )

    # Encounter validation
    encounter_spec = get_encounter_spec(encounter.encounter_id)
    if encounter_spec is None:
        return no_update, "This encounter is not supported for player analysis."
    try:
        prepared_analysis = PreparedPlayerAnalysis(
            encounter=encounter,
            player=player,
            phase_id=phase_id,
            encounter_level=encounter_spec.level,
            stats=stats,
        )
    except ValidationError:
        return no_update, "The selected player and encounter data are inconsistent."

    # See if the analysis has been done before
    # Redirect if it has been and isn't flagged for a recalc
    prior_analysis_id, needs_recalculation = search_prior_player_analyses(
        prepared_analysis.encounter.encounter_url.report_id,
        prepared_analysis.encounter.fight_id_resolved,
        prepared_analysis.phase_id,
        JOB_SPECS[prepared_analysis.player.job].fflogs_name,
        prepared_analysis.player.player_name,
        prepared_analysis.stats.main_stat_pre_bonus,
        prepared_analysis.stats.secondary_stat_pre_bonus,
        prepared_analysis.stats.determination,
        prepared_analysis.stats.speed_stat,
        prepared_analysis.stats.critical_hit,
        prepared_analysis.stats.direct_hit,
        prepared_analysis.stats.weapon_damage,
        prepared_analysis.stats.delay,
    )
    if prior_analysis_id is not None and not needs_recalculation:
        return f"/analysis/{prior_analysis_id}", ""

    try:
        rotation = build_rotation_table(prepared_analysis)
        job_result = rotation_analysis(
            prepared_analysis,
            rotation.rotation_df,
            rotation.fight_dps_time,
            action_delta=DISCRETIZATION_LEVEL_MAP[prepared_analysis.encounter_level],
        )
        distribution = PlayerDpsDistribution.from_job_analysis(
            job_result, rotation.fight_dps_time
        )
        rotation_dps = float(
            rotation.actions_df["amount"].sum() / distribution.active_dps_t
        )
        percentile = (
            get_dps_percentile(
                rotation_dps * distribution.active_dps_t / distribution.analysis_t,
                distribution.rotation_dps_distribution,
                distribution.rotation_dps_support,
            )
            / 100
        )

        analysis_id = str(uuid4())
        analysis_datetime = datetime.datetime.now()
        record = PlayerAnalysisRecord(
            analysis_id=analysis_id,
            report_id=prepared_analysis.encounter.encounter_url.report_id,
            fight_id=prepared_analysis.encounter.fight_id_resolved,
            phase_id=prepared_analysis.phase_id,
            encounter_name=rotation.fight_name,
            active_dps_time=distribution.active_dps_t,
            job=JOB_SPECS[prepared_analysis.player.job].fflogs_name,
            player_name=prepared_analysis.player.player_name,
            main_stat_pre_bonus=prepared_analysis.stats.main_stat_pre_bonus,
            main_stat=prepared_analysis.stats.main_stat,
            main_stat_type=prepared_analysis.stats.main_stat_type,
            secondary_stat_pre_bonus=prepared_analysis.stats.secondary_stat_pre_bonus,
            secondary_stat=prepared_analysis.stats.secondary_stat,
            secondary_stat_type=prepared_analysis.stats.secondary_stat_type,
            determination=prepared_analysis.stats.determination,
            speed=prepared_analysis.stats.speed_stat,
            critical_hit=prepared_analysis.stats.critical_hit,
            direct_hit=prepared_analysis.stats.direct_hit,
            weapon_damage=prepared_analysis.stats.weapon_damage,
            delay=prepared_analysis.stats.delay,
            medication_amount=-1,
            party_bonus=prepared_analysis.stats.party_bonus,
        )

        save_player_analysis_blobs(analysis_id, rotation, distribution)
        update_report_table(record)
        update_player_analysis_creation_table(
            PlayerAnalysisCreationRecord(
                analysis_id=analysis_id,
                creation_ts=analysis_datetime,
            )
        )
        update_access_table(
            PlayerAnalysisAccess(
                analysis_id=analysis_id,
                access_datetime=analysis_datetime,
            )
        )
    except Exception as error:
        error_record = PlayerAnalysisErrorRecord(
            report_id=prepared_analysis.encounter.encounter_url.report_id,
            fight_id=prepared_analysis.encounter.fight_id_resolved,
            player_id=prepared_analysis.player.player_id,
            encounter_id=prepared_analysis.encounter.encounter_id,
            encounter_name=prepared_analysis.encounter.encounter_name,
            phase_id=prepared_analysis.phase_id,
            job=JOB_SPECS[prepared_analysis.player.job].fflogs_name,
            player_name=prepared_analysis.player.player_name,
            main_stat_pre_bonus=prepared_analysis.stats.main_stat_pre_bonus,
            main_stat=prepared_analysis.stats.main_stat,
            main_stat_type=prepared_analysis.stats.main_stat_type,
            secondary_stat_pre_bonus=prepared_analysis.stats.secondary_stat_pre_bonus,
            secondary_stat=prepared_analysis.stats.secondary_stat,
            secondary_stat_type=prepared_analysis.stats.secondary_stat_type,
            determination=prepared_analysis.stats.determination,
            speed=prepared_analysis.stats.speed_stat,
            critical_hit=prepared_analysis.stats.critical_hit,
            direct_hit=prepared_analysis.stats.direct_hit,
            weapon_damage=prepared_analysis.stats.weapon_damage,
            delay=prepared_analysis.stats.delay,
            medication_amount=-1,
            party_bonus=prepared_analysis.stats.party_bonus,
            error_message=str(error),
            traceback=traceback.format_exc(),
        )
        try:
            insert_error_player_analysis(error_record)
        except Exception as logging_error:
            return (
                no_update,
                f"Player analysis failed: {error}. Error logging failed: {logging_error}",
            )
        return no_update, f"Player analysis failed: {error}"

    return f"/analysis/{analysis_id}", f"Analysis complete ({percentile:.1%})."
