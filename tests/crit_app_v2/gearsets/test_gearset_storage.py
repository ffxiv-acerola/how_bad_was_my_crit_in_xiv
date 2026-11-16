"""Tests for serializing the gearset library to and from browser storage."""

import json

import pytest

from crit_app_v2.game_data import STAT_INPUTS, Role, Stats
from crit_app_v2.gearsets import GearsetLibrary, SavedGearset, library_from_storage, library_to_storage


def _library() -> GearsetLibrary:
    """Create a small library with a default."""
    stats = {stat: STAT_INPUTS[stat].lower for stat in Stats}
    first = SavedGearset.from_form_values("Tank", Role.TANK, stats)
    second = SavedGearset.from_form_values("Healer", Role.HEALER, stats)
    return GearsetLibrary(gearsets=(first, second), default_id=second.id)


def test_storage_round_trip_preserves_library():
    """Restore an identical library from its stored form."""
    library = _library()

    assert library_from_storage(library_to_storage(library)) == library


def test_stored_form_is_json_serializable():
    """Produce plain JSON data that a dcc.Store can hold."""
    stored = library_to_storage(_library())

    assert json.loads(json.dumps(stored)) == stored


@pytest.mark.parametrize(
    "data",
    [
        None,
        "garbage",
        [],
        {"version": 2},
        {"gearsets": [{"name": "x"}]},
        {"default_id": "11111111-1111-4111-8111-111111111111"},
    ],
    ids=["none", "string", "list", "future-version", "incomplete-gearset", "dangling-default"],
)
def test_missing_or_invalid_data_loads_as_none(data):
    """Report absent or corrupted storage as None instead of raising."""
    assert library_from_storage(data) is None
