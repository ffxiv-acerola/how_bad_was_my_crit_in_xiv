"""Tests for validated models composing analysis inputs."""

import pytest
from pydantic import AnyHttpUrl, ValidationError

from crit_app_v2.analysis.models import PlayerAnalysisStats, PreparedPlayerAnalysis
from crit_app_v2.build_providers.models import RoleBuildStatsModel, ValidatedRoleBuild
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)
from crit_app_v2.game_data import JOB_SPECS, STAT_INPUTS, Job, Role, Stats


def _validated_build(role: Role) -> ValidatedRoleBuild:
    """Return a complete role build using canonical lower-bound stats."""
    stats = RoleBuildStatsModel(
        main_stat=STAT_INPUTS[Stats.MAIN_STAT].lower,
        determination=STAT_INPUTS[Stats.DETERMINATION].lower,
        speed_stat=STAT_INPUTS[Stats.SPEED_STAT].lower,
        critical_hit=STAT_INPUTS[Stats.CRITICAL_HIT].lower,
        direct_hit=STAT_INPUTS[Stats.DIRECT_HIT].lower,
        weapon_damage=STAT_INPUTS[Stats.WEAPON_DAMAGE].lower,
        tenacity=(STAT_INPUTS[Stats.TENACITY].lower if role is Role.TANK else None),
    )
    return ValidatedRoleBuild(role=role, stats=stats)


def _encounter() -> Encounter:
    """Build an encounter fixture with one Tank player."""
    player = EncounterPersonnel(
        player_name="Player",
        player_server="Test Server",
        player_id=12,
        pet_ids=[],
        job=Job.WARRIOR,
        role=Role.TANK,
    )
    return Encounter(
        encounter_url=EncounterUrl(build_url=AnyHttpUrl("https://www.fflogs.com/reports/abcdefghijklmnop?fight=7")),
        fight_id_resolved=7,
        encounter_id=93,
        encounter_name="Black Cat",
        last_phase_index=0,
        kill_time=100,
        excluded_enemy_ids=[],
        players=[player],
        limit_break=None,
    )


def test_tank_analysis_stats_keep_flat_derived_accessors() -> None:
    """Derive main stat, Tenacity metadata, and delay from validated inputs."""
    stats = PlayerAnalysisStats(
        job=Job.WARRIOR,
        build=_validated_build(Role.TANK),
        party_bonus=1.03,
    )

    assert stats.role is Role.TANK
    assert stats.main_stat == int(stats.main_stat_pre_bonus * 1.03)
    assert stats.main_stat_type == "strength"
    assert stats.secondary_stat_pre_bonus == stats.tenacity
    assert stats.secondary_stat == stats.tenacity
    assert stats.secondary_stat_type == "tenacity"
    assert stats.delay == JOB_SPECS[Job.WARRIOR].weapon_delay


def test_non_tank_analysis_stats_omit_tenacity_and_secondary_stat() -> None:
    """Non-Tank stats expose no secondary stat or Tenacity."""
    stats = PlayerAnalysisStats(
        job=Job.WHITE_MAGE,
        build=_validated_build(Role.HEALER),
        party_bonus=1.01,
    )

    assert stats.secondary_stat_pre_bonus is None
    assert stats.secondary_stat is None
    assert stats.secondary_stat_type is None


def test_player_analysis_stats_reject_job_from_another_role() -> None:
    """Require the selected job to belong to the validated role build."""
    with pytest.raises(ValidationError, match="is not a Healer job"):
        PlayerAnalysisStats(
            job=Job.WARRIOR,
            build=_validated_build(Role.HEALER),
            party_bonus=1.0,
        )


def test_prepared_player_analysis_accepts_encounter_member() -> None:
    """Compose a selected encounter player with valid analysis inputs."""
    encounter = _encounter()
    stats = PlayerAnalysisStats(
        job=Job.WARRIOR,
        build=_validated_build(Role.TANK),
        party_bonus=1.01,
    )

    prepared = PreparedPlayerAnalysis(
        encounter=encounter,
        player=encounter.players[0],
        phase_id=0,
        encounter_level=100,
        stats=stats,
    )

    assert prepared.player.player_id == 12
    assert prepared.encounter_level == 100


def test_prepared_player_analysis_rejects_player_outside_encounter() -> None:
    """Reject a selected player who is absent from the trusted encounter."""
    encounter = _encounter()
    stats = PlayerAnalysisStats(
        job=Job.WARRIOR,
        build=_validated_build(Role.TANK),
        party_bonus=1.01,
    )
    other_player = encounter.players[0].model_copy(update={"player_id": 99})

    with pytest.raises(ValidationError, match="not part of this encounter"):
        PreparedPlayerAnalysis(
            encounter=encounter,
            player=other_player,
            phase_id=0,
            encounter_level=100,
            stats=stats,
        )


def test_prepared_player_analysis_rejects_player_stats_role_mismatch() -> None:
    """Require prepared stats to match the encounter player's job and role."""
    encounter = _encounter()
    stats = PlayerAnalysisStats(
        job=Job.WHITE_MAGE,
        build=_validated_build(Role.HEALER),
        party_bonus=1.01,
    )

    with pytest.raises(ValidationError, match="job and role must match"):
        PreparedPlayerAnalysis(
            encounter=encounter,
            player=encounter.players[0],
            phase_id=0,
            encounter_level=100,
            stats=stats,
        )
