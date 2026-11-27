"""Construct role-specific DPS analyses from prepared player inputs."""

from typing import cast

import pandas as pd
from ffxiv_stats.jobs import Healer, MagicalRanged, Melee, PhysicalRanged, Tank

from crit_app_v2.analysis.dps_distribution import JobAnalysisResult
from crit_app_v2.analysis.models import PreparedPlayerAnalysis
from crit_app_v2.game_data import Role


def rotation_analysis(
    prepared: PreparedPlayerAnalysis,
    rotation_df: pd.DataFrame,
    analysis_time: float,
    *,
    rotation_delta: int = 100,
    rotation_step: float = 0.5,
    action_delta: int = 10,
    compute_mgf: bool = False,
) -> JobAnalysisResult:
    """Calculate DPS statistics for a prepared player's rotation.

    Parameters
    ----------
    prepared
        Validated player, encounter, and build analysis context.
    rotation_df
        Aggregated action rotation from ``fflogs_rotation.RotationTable``.
    analysis_time
        Fight time in seconds passed to the rotation analyzer.
    rotation_delta
        Rotation DPS discretization width.
    rotation_step
        Rotation PDF sampling step.
    action_delta
        Action DPS discretization width.
    compute_mgf
        Whether to compute the moment-generating function.

    Returns
    -------
    object
        Role-specific ``ffxiv_stats`` job analysis with attached rotation data.

    Raises
    ------
    ValueError
        If the rotation role is unsupported.
    """
    stats = prepared.stats
    match stats.role:
        case Role.HEALER:
            job_analysis = Healer(
                mind=stats.main_stat,
                strength=stats.secondary_stat or 0,
                det=stats.determination,
                spell_speed=stats.speed_stat,
                crit_stat=stats.critical_hit,
                dh_stat=stats.direct_hit,
                weapon_damage=stats.weapon_damage,
                delay=stats.delay,
                pet_attack_power=stats.main_stat_pre_bonus,
                level=prepared.encounter_level,
            )
        case Role.TANK:
            if stats.tenacity is None:
                raise ValueError("Tank rotation analysis requires Tenacity.")
            job_analysis = Tank(
                strength=stats.main_stat,
                det=stats.determination,
                skill_speed=stats.speed_stat,
                tenacity=stats.tenacity,
                crit_stat=stats.critical_hit,
                dh_stat=stats.direct_hit,
                weapon_damage=stats.weapon_damage,
                delay=stats.delay,
                job=prepared.player.job.value,
                pet_attack_power=stats.main_stat_pre_bonus,
                level=prepared.encounter_level,
            )
        case Role.MAGICAL_RANGED:
            job_analysis = MagicalRanged(
                intelligence=stats.main_stat,
                strength=stats.secondary_stat or 0,
                det=stats.determination,
                spell_speed=stats.speed_stat,
                crit_stat=stats.critical_hit,
                dh_stat=stats.direct_hit,
                weapon_damage=stats.weapon_damage,
                delay=stats.delay,
                pet_attack_power=stats.main_stat_pre_bonus,
                level=prepared.encounter_level,
            )
        case Role.MELEE:
            job_analysis = Melee(
                main_stat=stats.main_stat,
                det=stats.determination,
                skill_speed=stats.speed_stat,
                crit_stat=stats.critical_hit,
                dh_stat=stats.direct_hit,
                weapon_damage=stats.weapon_damage,
                delay=stats.delay,
                job=prepared.player.job.value,
                pet_attack_power=stats.main_stat_pre_bonus,
                level=prepared.encounter_level,
            )
        case Role.PHYSICAL_RANGED:
            job_analysis = PhysicalRanged(
                dexterity=stats.main_stat,
                det=stats.determination,
                skill_speed=stats.speed_stat,
                crit_stat=stats.critical_hit,
                dh_stat=stats.direct_hit,
                weapon_damage=stats.weapon_damage,
                delay=stats.delay,
                pet_attack_power=stats.main_stat_pre_bonus,
                level=prepared.encounter_level,
            )
        case _:
            raise ValueError(f"Unsupported player-analysis role: {stats.role!r}.")

    job_analysis.attach_rotation(
        rotation_df,
        analysis_time,
        rotation_delta=rotation_delta,
        rotation_pdf_step=rotation_step,
        action_delta=action_delta,
        purge_action_moments=True,
        compute_mgf=compute_mgf,
    )
    return cast(JobAnalysisResult, cast(object, job_analysis))
