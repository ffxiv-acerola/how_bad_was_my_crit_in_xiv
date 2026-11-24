"""Tests for the pre-rotation player-analysis callback flow."""

from unittest.mock import patch

import dash
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


def test_analysis_callback_uses_server_encounter_and_stops_before_rotation(
    monkeypatch,
) -> None:
    """Resolve validated stats and prior lookup before the rotation boundary."""
    encounter = _encounter()
    monkeypatch.setattr("crit_app_v2.pages.analysis.load_encounter", lambda _report, _fight: encounter)
    prior_searches: list[tuple] = []

    def search_prior(*args):
        prior_searches.append(args)
        return None, False

    monkeypatch.setattr("crit_app_v2.pages.analysis.search_prior_player_analyses", search_prior)

    result = _analyze(encounter)

    assert result == (
        dash.no_update,
        "Pre-analysis checks complete; rotation analysis is not implemented yet.",
    )
    assert len(prior_searches) == 1
    assert prior_searches[0][3:6] == ("Warrior", "Player", 4000)
    assert prior_searches[0][6] == 500


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
