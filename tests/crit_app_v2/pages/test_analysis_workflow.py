"""Tests for the pre-rotation player-analysis callback flow."""

from types import SimpleNamespace
from unittest.mock import patch

import dash
import numpy as np
import pandas as pd
import pytest
from pydantic import AnyHttpUrl

from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)
from crit_app_v2.game_data import Job, Role
from crit_app_v2.ui.fflogs_encounter import encounter_to_store

with patch("dash.register_page"):
    from crit_app_v2.pages.analysis import (
        analyze_and_register_rotation,
        load_encounter_from_url,
    )


def _encounter() -> Encounter:
    """Build a validated encounter fixture with one Tank player."""
    return Encounter(
        encounter_url=EncounterUrl(build_url=AnyHttpUrl("https://www.fflogs.com/reports/abcdefghijklmnop?fight=7")),
        fight_id_resolved=7,
        encounter_id=93,
        encounter_name="Black Cat",
        last_phase_index=0,
        kill_time=100,
        excluded_enemy_ids=[],
        players=[
            EncounterPersonnel(
                player_name="Player",
                player_server="Test Server",
                player_id=12,
                pet_ids=[],
                job=Job.WARRIOR,
                role=Role.TANK,
            )
        ],
        limit_break=None,
    )


def _analyze(encounter: Encounter, *, url: str | None = None):
    """Call the player-analysis callback with a valid Warrior build draft."""
    return analyze_and_register_rotation(
        1,
        Role.TANK.value,
        4000,
        1500,
        400,
        2000,
        1000,
        100,
        500,
        encounter_to_store(encounter),
        url or "https://www.fflogs.com/reports/abcdefghijklmnop?fight=7",
        "0",
        "12",
    )


def test_encounter_load_callback_persists_supported_server_response(
    monkeypatch,
) -> None:
    """Persist the fetched model before returning it to the browser store."""
    encounter = _encounter()
    saved: list[Encounter] = []
    monkeypatch.setattr("crit_app_v2.pages.analysis.fetch_encounter", lambda _url: encounter)
    monkeypatch.setattr("crit_app_v2.pages.analysis.save_encounter", saved.append)

    result = load_encounter_from_url(1, "https://fflogs.example", Role.TANK.value)

    assert saved == [encounter]
    assert result[0] == encounter_to_store(encounter)


def test_analysis_callback_completes_rotation_and_persists_result(
    monkeypatch,
) -> None:
    """Run the full analysis flow and persist its result before redirecting."""
    encounter = _encounter()
    monkeypatch.setattr("crit_app_v2.pages.analysis.load_encounter", lambda _report, _fight: encounter)
    prior_searches: list[tuple] = []

    def search_prior(*args):
        prior_searches.append(args)
        return None, False

    monkeypatch.setattr("crit_app_v2.pages.analysis.search_prior_player_analyses", search_prior)
    rotation = SimpleNamespace(
        rotation_df=pd.DataFrame({"action": ["test"]}),
        actions_df=pd.DataFrame({"amount": [10000]}),
        fight_dps_time=100.0,
        fight_name="Black Cat",
        fight_start_time=0,
    )
    monkeypatch.setattr("crit_app_v2.pages.analysis.build_rotation_table", lambda _prepared: rotation)
    monkeypatch.setattr(
        "crit_app_v2.pages.analysis.rotation_analysis",
        lambda *_args, **_kwargs: SimpleNamespace(
            t=100.0,
            rotation_mean=100.0,
            rotation_variance=1.0,
            rotation_std=1.0,
            rotation_skewness=0.0,
            rotation_dps_distribution=np.array([0.0002, 0.0004, 0.0002]),
            rotation_dps_support=np.array([1000.0, 1500.0, 2000.0]),
            unique_actions_distribution={
                "Test Action": {
                    "support": np.array([1000.0, 1500.0, 2000.0]),
                    "dps_distribution": np.array([0.0002, 0.0004, 0.0002]),
                }
            },
        ),
    )
    saved_records = []
    monkeypatch.setattr("crit_app_v2.pages.analysis.save_player_analysis_blobs", lambda *args: None)
    monkeypatch.setattr("crit_app_v2.pages.analysis.update_report_table", saved_records.append)
    monkeypatch.setattr("crit_app_v2.pages.analysis.update_player_analysis_creation_table", lambda _record: None)
    accesses = []
    monkeypatch.setattr("crit_app_v2.pages.analysis.update_access_table", accesses.append)
    monkeypatch.setattr("crit_app_v2.pages.analysis.uuid4", lambda: "new-id")

    result = _analyze(encounter)

    assert result == (
        "/analysis/new-id",
        "Analysis complete (10.0%).",
    )
    assert len(prior_searches) == 1
    assert prior_searches[0][3:6] == ("Warrior", "Player", 4000)
    assert prior_searches[0][6] == 500
    assert saved_records[0].analysis_id == "new-id"
    assert saved_records[0].medication_amount == -1
    assert accesses[0].analysis_id == "new-id"


def test_analysis_callback_redirects_to_existing_analysis(monkeypatch) -> None:
    """Redirect to an existing matching analysis when no recalculation is due."""
    encounter = _encounter()
    monkeypatch.setattr("crit_app_v2.pages.analysis.load_encounter", lambda _report, _fight: encounter)
    monkeypatch.setattr(
        "crit_app_v2.pages.analysis.search_prior_player_analyses",
        lambda *_args: ("prior-id", False),
    )

    assert _analyze(encounter) == ("/analysis/prior-id", "")


def test_analysis_callback_rejects_stale_fflogs_url(monkeypatch) -> None:
    """Require a URL resubmit when the input no longer matches the loaded fight."""
    encounter = _encounter()
    monkeypatch.setattr(
        "crit_app_v2.pages.analysis.load_encounter",
        lambda *_args: pytest.fail("stale URL should be rejected before database access"),
    )

    result = _analyze(
        encounter,
        url="https://www.fflogs.com/reports/abcdefghijklmnop?fight=8",
    )

    assert result == (
        dash.no_update,
        "Please resubmit the FFLogs URL; the encounter changed.",
    )
