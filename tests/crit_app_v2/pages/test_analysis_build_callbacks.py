"""Tests for loading provider builds into the analysis form."""

from unittest.mock import patch

import dash
from pydantic import AnyHttpUrl

from crit_app_v2.build_providers import (
    BuildErrorCategory,
    BuildProvider,
    BuildProviderError,
    BuildUrl,
    LoadedXivGearBuild,
    RoleBuildStatsModel,
)
from crit_app_v2.build_providers.models.etro_models import LoadedEtroBuild
from crit_app_v2.build_providers.models.xivgear_models import LoadedXivGearSet
from crit_app_v2.game_data import STAT_INPUTS, Role, Stats

with patch("dash.register_page"):
    from crit_app_v2.pages.analysis import (
        _xiv_gear_selector_state,
        apply_loaded_job_build,
        job_build_validator,
        load_job_build_from_url,
    )


def _xiv_gear_build(*, selected_index: int | None = None):
    return LoadedXivGearBuild(
        build_url=BuildUrl(build_url=AnyHttpUrl("https://xivgear.app/?page=sl%7C11111111-1111-4111-8111-111111111111")),
        build_index=selected_index,
        build_role=Role.TANK,
        sets=[
            LoadedXivGearSet(
                response_index=0,
                build_name="First set",
                build_stats=RoleBuildStatsModel(
                    main_stat=4800,
                    determination=2000,
                    speed_stat=400,
                    critical_hit=2500,
                    direct_hit=1000,
                    weapon_damage=145,
                    tenacity=500,
                ),
            ),
            LoadedXivGearSet(
                response_index=2,
                build_name="Second set",
                build_stats=RoleBuildStatsModel(
                    main_stat=4900,
                    determination=2100,
                    speed_stat=450,
                    critical_hit=2600,
                    direct_hit=1100,
                    weapon_damage=146,
                    tenacity=550,
                ),
            ),
        ],
    )


def test_xiv_gear_selector_uses_original_response_indexes():
    """Keep selector values aligned with indexes retained by the provider."""
    options, style, value = _xiv_gear_selector_state(_xiv_gear_build(selected_index=2))

    assert options == [
        {"label": "First set", "value": "0"},
        {"label": "Second set", "value": "2"},
    ]
    assert style == {}
    assert value == "2"


def test_apply_loaded_xiv_gear_set_populates_role_and_selected_stats():
    """Apply the selected set by its response index, not its visible offset."""
    values = apply_loaded_job_build(_xiv_gear_build().model_dump(mode="json"), "2")

    assert values == (Role.TANK.value, 4900, 2100, 450, 2600, 1100, 146, 550)


def test_apply_loaded_xiv_gear_without_selection_leaves_manual_values_alone():
    """Do not clear manually entered stats while a multi-set sheet is unselected."""
    values = apply_loaded_job_build(_xiv_gear_build().model_dump(mode="json"), None)

    assert values == (dash.no_update,) * 8


def test_apply_loaded_etro_build_populates_role_and_stats():
    """Apply the single normalized Etro build directly to the form."""
    build = LoadedEtroBuild(
        build_url=BuildUrl(build_url=AnyHttpUrl("https://etro.gg/gearset/11111111-1111-4111-8111-111111111111")),
        build_id="11111111-1111-4111-8111-111111111111",
        build_name="Test Etro set",
        build_role=Role.HEALER,
        build_stats=RoleBuildStatsModel(
            main_stat=4800,
            determination=2000,
            speed_stat=1900,
            critical_hit=2500,
            direct_hit=1000,
            weapon_damage=145,
            tenacity=None,
        ),
    )

    values = apply_loaded_job_build(build.model_dump(mode="json"), None)

    assert values == ("Healer", 4800, 2000, 1900, 2500, 1000, 145, None)


def test_provider_load_callback_serializes_loaded_build(monkeypatch):
    """Store normalized provider data and expose multi-set selection choices."""
    build = _xiv_gear_build(selected_index=2)
    monkeypatch.setattr("crit_app_v2.pages.analysis.validate_job_build_url", lambda url: url)
    monkeypatch.setattr("crit_app_v2.pages.analysis.load_job_build", lambda url: build)

    result = load_job_build_from_url(1, "https://xivgear.app/?page=sl%7Cexample")

    assert result[0] == build.model_dump(mode="json")
    assert result[1] is None
    assert result[2][1] == {"label": "Second set", "value": "2"}
    assert result[3] == {}
    assert result[4] == "2"


def test_invalid_or_unsupported_url_has_friendly_feedback(monkeypatch):
    """Avoid exposing URL parser details for unsupported input."""

    def reject_url(_url):
        raise BuildProviderError(BuildErrorCategory.INVALID_URL)

    monkeypatch.setattr(
        "crit_app_v2.pages.analysis.validate_job_build_url",
        reject_url,
    )

    result = load_job_build_from_url(1, "https://example.com/build")

    assert result[1] == ("Invalid or unsupported URL. Enter a valid Etro or XIVGear build URL.")


def test_provider_load_callback_renders_normalized_error(monkeypatch):
    """Render typed provider errors through the shared UI adapter."""
    monkeypatch.setattr(
        "crit_app_v2.pages.analysis.validate_job_build_url",
        lambda url: BuildUrl(build_url=AnyHttpUrl("https://xivgear.app")),
    )

    def reject_build(_build_url):
        raise BuildProviderError(
            BuildErrorCategory.PROVIDER_UNAVAILABLE,
            provider=BuildProvider.XIV_GEAR,
            status_code=500,
        )

    monkeypatch.setattr("crit_app_v2.pages.analysis.load_job_build", reject_build)

    result = load_job_build_from_url(1, "https://xivgear.app/?page=broken")

    assert result[1] == ("XIVGear couldn't load this build. Check the link or try again later.")


def test_job_build_validator_accepts_role_value_from_dash():
    """Convert the Dash string role before draft validation checks Tenacity."""
    values = {stat: STAT_INPUTS[stat].lower for stat in Stats}
    result = job_build_validator(
        Role.TANK.value,
        values[Stats.MAIN_STAT],
        values[Stats.DETERMINATION],
        values[Stats.SPEED_STAT],
        values[Stats.CRITICAL_HIT],
        values[Stats.DIRECT_HIT],
        values[Stats.WEAPON_DAMAGE],
        values[Stats.TENACITY],
    )

    assert result[0] is False
