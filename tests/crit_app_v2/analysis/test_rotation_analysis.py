"""Tests for role-specific construction of player rotation analysis."""

from typing import Any

import pandas as pd
import pytest
from pydantic import AnyHttpUrl

from crit_app_v2.analysis.models import PlayerAnalysisStats, PreparedPlayerAnalysis
from crit_app_v2.analysis.rotation_analysis import rotation_analysis
from crit_app_v2.build_providers.models import RoleBuildStatsModel, ValidatedRoleBuild
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)
from crit_app_v2.game_data import STAT_INPUTS, Job, Role, Stats


def _prepared(role: Role, job: Job) -> PreparedPlayerAnalysis:
    """Build a validated analysis fixture for a selected role and job."""
    player = EncounterPersonnel(
        player_name="Tester",
        player_server="Server",
        player_id=21,
        pet_ids=[],
        job=job,
        role=role,
    )
    encounter = Encounter(
        encounter_url=EncounterUrl(build_url=AnyHttpUrl("https://www.fflogs.com/reports/abcdefghijklmnop?fight=2")),
        fight_id_resolved=2,
        encounter_id=93,
        encounter_name="Encounter",
        last_phase_index=0,
        kill_time=100,
        excluded_enemy_ids=[],
        players=[player],
        limit_break=None,
    )
    stats = RoleBuildStatsModel(
        main_stat=STAT_INPUTS[Stats.MAIN_STAT].lower,
        determination=STAT_INPUTS[Stats.DETERMINATION].lower,
        speed_stat=STAT_INPUTS[Stats.SPEED_STAT].lower,
        critical_hit=STAT_INPUTS[Stats.CRITICAL_HIT].lower,
        direct_hit=STAT_INPUTS[Stats.DIRECT_HIT].lower,
        weapon_damage=STAT_INPUTS[Stats.WEAPON_DAMAGE].lower,
        tenacity=(STAT_INPUTS[Stats.TENACITY].lower if role is Role.TANK else None),
    )
    player_stats = PlayerAnalysisStats(
        job=job,
        build=ValidatedRoleBuild(role=role, stats=stats),
        party_bonus=1.01,
    )
    return PreparedPlayerAnalysis(
        encounter=encounter,
        player=player,
        phase_id=0,
        encounter_level=100,
        stats=player_stats,
    )


class _FakeJobAnalysis:
    """Capture rotation attachment options in role-dispatch tests."""

    def __init__(self, role_name: str, **kwargs: Any) -> None:
        self.role_name = role_name
        self.kwargs = kwargs

    def attach_rotation(self, rotation_df: pd.DataFrame, analysis_time: float, **kwargs: Any) -> None:
        """Store the supplied rotation inputs for test assertions."""
        self.rotation_df = rotation_df
        self.analysis_time = analysis_time
        self.rotation_options = kwargs


@pytest.mark.parametrize(
    "role,job,expected",
    [
        (Role.HEALER, Job.WHITE_MAGE, "healer"),
        (Role.TANK, Job.WARRIOR, "tank"),
        (Role.MAGICAL_RANGED, Job.BLACK_MAGE, "magical"),
        (Role.MELEE, Job.DRAGOON, "melee"),
        (Role.PHYSICAL_RANGED, Job.BARD, "physical"),
    ],
    ids=["healer", "tank", "magical-ranged", "melee", "physical-ranged"],
)
def test_rotation_analysis_dispatches_by_validated_role(
    monkeypatch: pytest.MonkeyPatch,
    role: Role,
    job: Job,
    expected: str,
) -> None:
    """Construct the matching stats job and attach its rotation data."""
    import crit_app_v2.analysis.rotation_analysis as module

    for role_name, class_name in (
        ("healer", "Healer"),
        ("tank", "Tank"),
        ("magical", "MagicalRanged"),
        ("melee", "Melee"),
        ("physical", "PhysicalRanged"),
    ):
        monkeypatch.setattr(
            module,
            class_name,
            lambda *args, _role_name=role_name, **kwargs: _FakeJobAnalysis(_role_name, **kwargs),
        )
    rotation_df = pd.DataFrame({"action": ["test"]})

    result = rotation_analysis(_prepared(role, job), rotation_df, 95.0)

    assert result.role_name == expected
    assert result.rotation_df is rotation_df
    assert result.analysis_time == 95.0
    assert result.rotation_options["action_delta"] == 10
