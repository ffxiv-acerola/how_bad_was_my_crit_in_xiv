"""Tests for migrating legacy saved gearsets."""

import pytest

from crit_app_v2.game_data import Role
from crit_app_v2.gearsets import MAX_GEARSET_NAME_LENGTH, MAX_SAVED_GEARSETS, migrate_legacy_gearsets


def _legacy(role: str = "Healer", name: str = "Set", **overrides) -> dict:
    """Create a legacy gearset record using the old key names."""
    record = {
        "role": role,
        "name": name,
        "main_stat": 4000,
        "determination": 2000,
        "speed": 500,
        "crit": 2500,
        "direct_hit": 1000,
        "weapon_damage": 140,
        "is_selected": False,
    }
    if role == "Tank":
        record["tenacity"] = 600
    record.update(overrides)
    return record


def test_legacy_keys_map_to_current_stats():
    """Map abbreviated legacy keys onto the current stat names."""
    result = migrate_legacy_gearsets([_legacy("Tank", "Tank set")], None)

    stats = result.library.gearsets[0].stats
    assert (stats.speed_stat, stats.critical_hit, stats.direct_hit, stats.tenacity) == (500, 2500, 1000, 600)
    assert result.library.gearsets[0].role is Role.TANK
    assert result.skipped == 0


def test_order_and_duplicate_names_are_preserved():
    """Keep the saved order and allow repeated names."""
    result = migrate_legacy_gearsets([_legacy(name="A"), _legacy(name="A"), _legacy(name="B")], None)

    assert [g.name for g in result.library.gearsets] == ["A", "A", "B"]
    assert len({g.id for g in result.library.gearsets}) == 3


@pytest.mark.parametrize("default_index", [1, "1", 1.0], ids=["int", "string", "float"])
def test_default_index_resolves_to_gearset_id(default_index):
    """Resolve the legacy default index to the migrated gearset's ID."""
    result = migrate_legacy_gearsets([_legacy(name="A"), _legacy(name="B")], default_index)

    assert result.library.default_gearset.name == "B"


@pytest.mark.parametrize(
    "default_index",
    [None, "", "abc", -1, 5, True],
    ids=["none", "empty", "garbage", "negative", "out-of-range", "bool"],
)
def test_unusable_default_index_means_no_default(default_index):
    """Ignore default indexes that do not identify a migrated gearset."""
    result = migrate_legacy_gearsets([_legacy(name="A")], default_index)

    assert result.library.default_id is None


def test_default_follows_its_gearset_when_earlier_records_are_skipped():
    """Resolve the default against original positions, not post-skip positions."""
    result = migrate_legacy_gearsets([_legacy(main_stat=1), _legacy(name="Keep")], 1)

    assert result.skipped == 1
    assert result.library.default_gearset.name == "Keep"


def test_default_pointing_at_skipped_record_is_dropped():
    """Clear the default when its record could not be migrated."""
    result = migrate_legacy_gearsets([_legacy(name="Keep"), _legacy(main_stat=1)], 1)

    assert result.library.default_id is None
    assert [g.name for g in result.library.gearsets] == ["Keep"]


@pytest.mark.parametrize(
    "record",
    [
        _legacy("Tank", tenacity=None),
        _legacy("Unsupported"),
        _legacy(crit=None),
        _legacy(weapon_damage=9999),
        "not a dict",
        None,
    ],
    ids=["tank-without-tenacity", "unknown-role", "missing-stat", "out-of-range", "string", "none"],
)
def test_unusable_records_are_skipped_and_counted(record):
    """Skip records that cannot be a valid gearset instead of failing the import."""
    result = migrate_legacy_gearsets([record, _legacy(name="Good")], None)

    assert result.skipped == 1
    assert [g.name for g in result.library.gearsets] == ["Good"]


def test_stale_tenacity_on_non_tank_is_dropped():
    """Ignore leftover Tenacity on non-Tank records rather than rejecting them."""
    result = migrate_legacy_gearsets([_legacy("Healer", tenacity=600)], None)

    assert result.library.gearsets[0].stats.tenacity is None


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [(None, "Unnamed"), ("   ", "Unnamed"), (42, "Unnamed"), ("x" * 200, "x" * MAX_GEARSET_NAME_LENGTH)],
    ids=["none", "blank", "non-string", "too-long"],
)
def test_names_are_normalized(raw_name, expected):
    """Replace blank names and truncate long ones instead of dropping the set."""
    result = migrate_legacy_gearsets([_legacy(name=raw_name)], None)

    assert result.library.gearsets[0].name == expected


def test_records_beyond_the_limit_are_skipped():
    """Cap the migrated library at the maximum size."""
    result = migrate_legacy_gearsets([_legacy(name=str(i)) for i in range(MAX_SAVED_GEARSETS + 3)], None)

    assert len(result.library.gearsets) == MAX_SAVED_GEARSETS
    assert result.skipped == 3


@pytest.mark.parametrize("stored", [None, {}, "text", 5], ids=["none", "dict", "string", "number"])
def test_non_list_store_yields_empty_library(stored):
    """Treat a missing or malformed legacy store as having no gearsets."""
    result = migrate_legacy_gearsets(stored, 0)

    assert result.library.gearsets == ()
    assert result.skipped == 0
