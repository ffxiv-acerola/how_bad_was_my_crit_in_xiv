"""Build action-level rotation tables from validated player-analysis context."""

from typing import Protocol, cast

import pandas as pd

from crit_app_v2.analysis.models import PreparedPlayerAnalysis
from crit_app_v2.fflogs_encounters.client import fflogs_headers
from crit_app_v2.game_data import JOB_SPECS
from crit_app_v2.game_data.encounters import ENCOUNTER_PHASES
from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable


class RotationTableResult(Protocol):
    """Rotation fields required by the player-analysis workflow."""

    rotation_df: pd.DataFrame
    actions_df: pd.DataFrame
    fight_dps_time: float
    fight_name: str
    fight_start_time: float


def build_rotation_table(prepared: PreparedPlayerAnalysis) -> RotationTableResult:
    """Fetch FFLogs actions and construct the selected player's rotation table.

    Parameters
    ----------
    prepared
        Validated player, encounter, and build analysis context.

    Returns
    -------
    RotationTable
        Rotation table with normalized fight events and aggregated actions.
    """
    encounter = prepared.encounter
    stats = prepared.stats
    job = prepared.player.job
    phase_spec = ENCOUNTER_PHASES.get(encounter.encounter_id)
    phases = (
        {index: name for index, name in enumerate(phase_spec.phase_names, start=1)}
        if phase_spec is not None
        else {}
    )
    rotation = RotationTable(
        fflogs_headers(),
        encounter.encounter_url.report_id,
        encounter.fight_id_resolved,
        JOB_SPECS[job].fflogs_name,
        prepared.player.player_id,
        stats.critical_hit,
        stats.direct_hit,
        stats.determination,
        stats.main_stat,
        stats.weapon_damage,
        prepared.encounter_level,
        prepared.phase_id,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        phases,
        prepared.player.pet_ids,
        encounter.excluded_enemy_ids,
        stats.tenacity,
    )
    if rotation.rotation_df is None:
        raise ValueError("No rotation actions were found for the selected phase.")
    return cast(RotationTableResult, cast(object, rotation))
