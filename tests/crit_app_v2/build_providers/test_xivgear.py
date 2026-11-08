"""Tests for loading and processing XIVGear build data."""

from typing import Any

import pytest
from pydantic import AnyHttpUrl

from crit_app_v2.build_providers import BuildErrorCategory, BuildProviderError
from crit_app_v2.build_providers.models import BuildProvider, BuildUrl
from crit_app_v2.build_providers.xivgear import (
    _gearset_index,
    _process_xiv_gear_set,
    load_xiv_gear_build,
)
from crit_app_v2.game_data import Role


def build_url(
    url: str = "https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111",
) -> BuildUrl:
    """Return a validated XIVGear URL for provider tests."""
    return BuildUrl(build_url=AnyHttpUrl(url))


def xivgear_set(
    *,
    job: str = "SCH",
    name: str = "Test set",
    is_separator: bool = False,
) -> dict[str, Any]:
    """Build a minimal API set containing the stats used by the loader."""
    return {
        "name": name,
        "isSeparator": is_separator,
        "computedStats": {
            "job": job,
            "mind": 4886,
            "strength": 5000,
            "dexterity": 4000,
            "intelligence": 4500,
            "determination": 2390,
            "skillspeed": 420,
            "spellspeed": 1985,
            "crit": 2787,
            "dhit": 474,
            "wdMag": 146,
            "wdPhys": 145,
            "tenacity": 420,
        },
    }


def xivgear_response(*sets: dict[str, Any]) -> dict[str, Any]:
    """Wrap set entries in the response structure used by the provider."""
    return {"sets": list(sets)}


def test_gearset_index_defaults_single_response_to_zero():
    """Treat a one-set API response as the selected set."""
    url = build_url("https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111&onlySetIndex=3")

    assert _gearset_index(url.build_url, xivgear_response(xivgear_set())) == 0


def test_gearset_index_reads_selected_index_for_sheet_response():
    """Resolve selectedIndex against the returned sets array."""
    url = build_url("https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111&selectedIndex=1")
    response = xivgear_response(xivgear_set(name="First"), xivgear_set(name="Second"))

    assert _gearset_index(url.build_url, response) == 1


def test_gearset_index_is_none_when_sheet_has_no_selection():
    """Leave selection unset when a multi-set URL selects no entry."""
    url = build_url()
    response = xivgear_response(xivgear_set(name="First"), xivgear_set(name="Second"))

    assert _gearset_index(url.build_url, response) is None


@pytest.mark.parametrize(
    "selected_index",
    ["invalid", "-1", "2"],
    ids=["not-an-integer", "negative", "past-end"],
)
def test_gearset_index_rejects_malformed_or_out_of_range_selection(selected_index):
    """Reject non-integer and out-of-range response indexes."""
    url = build_url(f"https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111&selectedIndex={selected_index}")
    response = xivgear_response(xivgear_set(), xivgear_set())

    with pytest.raises(BuildProviderError) as error:
        _gearset_index(url.build_url, response)
    assert error.value.category is BuildErrorCategory.REJECTED


def test_gearset_index_rejects_selection_of_separator():
    """Do not allow a selected response index to point at a separator row."""
    url = build_url("https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111&selectedIndex=0")
    response = xivgear_response(xivgear_set(is_separator=True), xivgear_set())

    with pytest.raises(BuildProviderError) as error:
        _gearset_index(url.build_url, response)
    assert error.value.category is BuildErrorCategory.REJECTED


def test_process_xiv_gear_set_maps_job_role_stats_and_original_index():
    """Use job metadata to produce role-only stats from computedStats."""
    role, loaded_set = _process_xiv_gear_set(xivgear_set(), response_index=3)

    assert role is Role.HEALER
    assert loaded_set.response_index == 3
    assert loaded_set.build_name == "Test set"
    assert loaded_set.build_stats.model_dump() == {
        "main_stat": 4886,
        "determination": 2390,
        "speed_stat": 1985,
        "critical_hit": 2787,
        "direct_hit": 474,
        "weapon_damage": 146,
        "tenacity": None,
    }


@pytest.mark.parametrize(
    ("job", "role", "main_stat", "speed_stat", "weapon_damage", "tenacity"),
    [
        ("PLD", Role.TANK, 5000, 420, 145, 420),
        ("NIN", Role.MELEE, 4000, 420, 145, None),
        ("MCH", Role.PHYSICAL_RANGED, 4000, 420, 145, None),
        ("PCT", Role.MAGICAL_RANGED, 4500, 1985, 146, None),
    ],
    ids=["tank", "melee", "physical-ranged", "magical-ranged"],
)
def test_process_xiv_gear_set_uses_job_and_role_metadata(job, role, main_stat, speed_stat, weapon_damage, tenacity):
    """Select main, speed, weapon-damage, and Tenacity stats by role/job."""
    actual_role, loaded_set = _process_xiv_gear_set(xivgear_set(job=job), 0)

    assert actual_role is role
    assert loaded_set.build_stats.main_stat == main_stat
    assert loaded_set.build_stats.speed_stat == speed_stat
    assert loaded_set.build_stats.weapon_damage == weapon_damage
    assert loaded_set.build_stats.tenacity == tenacity


def test_load_xiv_gear_build_filters_separators_and_keeps_response_indexes(
    monkeypatch,
):
    """Keep only usable sets while preserving their indexes in the response."""
    url = build_url("https://xivgear.app/?page=sl|11111111-1111-4111-8111-111111111111&selectedIndex=2")
    response = xivgear_response(
        xivgear_set(name="First"),
        xivgear_set(is_separator=True),
        xivgear_set(name="Duplicate"),
        xivgear_set(name="Duplicate"),
    )
    monkeypatch.setattr(
        "crit_app_v2.build_providers.xivgear._query_xiv_gear_sets",
        lambda raw_url: response,
    )

    loaded = load_xiv_gear_build(url)

    assert loaded.build_role is Role.HEALER
    assert loaded.build_index == 2
    assert [set_.response_index for set_ in loaded.sets] == [0, 2, 3]
    assert [set_.build_name for set_ in loaded.sets] == [
        "First",
        "Duplicate",
        "Duplicate",
    ]


def test_load_xiv_gear_build_rejects_multiple_roles(monkeypatch):
    """Reject a sheet whose sets cannot be represented by one build role."""
    url = build_url()
    response = xivgear_response(xivgear_set(job="SCH"), xivgear_set(job="PLD"))
    monkeypatch.setattr(
        "crit_app_v2.build_providers.xivgear._query_xiv_gear_sets",
        lambda raw_url: response,
    )

    with pytest.raises(BuildProviderError) as error:
        load_xiv_gear_build(url)
    assert error.value.category is BuildErrorCategory.REJECTED


def test_load_xiv_gear_build_rejects_truncated_share_uuid_before_request(
    monkeypatch,
):
    """Give an actionable error without requesting a known malformed share URL."""
    url = build_url("https://xivgear.app/?page=sl%7Cff8e55a8-a598-4bf3-abd")

    def unexpected_request(_raw_url):
        pytest.fail("Malformed share identifiers should be rejected locally.")

    monkeypatch.setattr(
        "crit_app_v2.build_providers.xivgear._query_xiv_gear_sets",
        unexpected_request,
    )

    with pytest.raises(BuildProviderError) as error:
        load_xiv_gear_build(url)
    assert error.value.category is BuildErrorCategory.REJECTED
    assert error.value.provider is BuildProvider.XIV_GEAR


@pytest.mark.parametrize(
    "url",
    [
        "https://xivgear.app/?page=sl%7C11111111-1111-4111-8111-111111111111",
        "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios",
        "https://share.xivgear.app/share/11111111-1111-4111-8111-111111111111",
    ],
    ids=["single-job-query", "bis-page", "share-path"],
)
def test_recognized_valid_or_unvalidated_xivgear_links_are_not_rejected_locally(
    url,
    monkeypatch,
):
    """Validate recognizable share IDs but defer other valid routes to XIVGear."""
    monkeypatch.setattr(
        "crit_app_v2.build_providers.xivgear._query_xiv_gear_sets",
        lambda raw_url: {"sets": []},
    )
    build = build_url(url)

    with pytest.raises(BuildProviderError) as error:
        load_xiv_gear_build(build)
    assert error.value.category is BuildErrorCategory.REJECTED
