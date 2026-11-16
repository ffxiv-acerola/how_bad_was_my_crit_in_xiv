"""Tests for saved-gearset models and library operations."""

import pytest
from pydantic import ValidationError

from crit_app_v2.build_providers import BuildProvider
from crit_app_v2.game_data import ROLE_SPECS, STAT_INPUTS, Role, Stats
from crit_app_v2.gearsets import (
    MAX_GEARSET_NAME_LENGTH,
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    GearsetLimitError,
    GearsetNotFoundError,
    SavedGearset,
)


def _stats(role: Role, **overrides) -> dict[Stats, int | None]:
    """Build valid form values for a role, using each stat's lower bound."""
    values: dict[Stats, int | None] = {stat: STAT_INPUTS[stat].lower for stat in Stats}
    if not ROLE_SPECS[role].requires_tenacity:
        values[Stats.TENACITY] = None
    values.update({Stats(key): value for key, value in overrides.items()})
    return values


def _gearset(name: str = "Set", role: Role = Role.HEALER, **overrides) -> SavedGearset:
    """Create a valid saved gearset."""
    return SavedGearset.from_form_values(name, role, _stats(role, **overrides))


def _library(count: int) -> GearsetLibrary:
    """Create a library holding ``count`` distinct gearsets."""
    library = GearsetLibrary()
    for index in range(count):
        library = library.add(_gearset(f"Set {index}"))
    return library


@pytest.mark.parametrize("role", list(Role), ids=[role.name.lower() for role in Role])
def test_valid_gearset_for_every_role(role):
    """Accept a complete build for each role, with Tenacity only for Tanks."""
    gearset = _gearset(role=role)

    assert gearset.role is role
    assert (gearset.stats.tenacity is not None) is ROLE_SPECS[role].requires_tenacity


@pytest.mark.parametrize("stat", [stat for stat in Stats if stat is not Stats.TENACITY], ids=lambda stat: stat.value)
@pytest.mark.parametrize("bound", ["below", "above"])
def test_stat_outside_canonical_range_is_rejected(stat, bound):
    """Reject stats outside the canonical STAT_INPUTS limits."""
    stat_range = STAT_INPUTS[stat]
    value = stat_range.lower - 1 if bound == "below" else stat_range.upper + 1

    with pytest.raises(ValidationError):
        _gearset(**{stat.value: value})


def test_tank_requires_tenacity():
    """Reject a Tank gearset that has no Tenacity."""
    with pytest.raises(ValidationError):
        _gearset(role=Role.TANK, tenacity=None)


def test_non_tank_must_not_provide_tenacity_in_the_model():
    """Reject Tenacity on a non-Tank when constructing the model directly."""
    tank = _gearset(role=Role.TANK)

    with pytest.raises(ValidationError):
        SavedGearset(name="Healer", role=Role.HEALER, stats=tank.stats)


def test_from_form_values_ignores_stale_hidden_tenacity():
    """Drop Tenacity left in the hidden input when the role is not a Tank."""
    values = _stats(Role.HEALER)
    values[Stats.TENACITY] = STAT_INPUTS[Stats.TENACITY].lower

    assert SavedGearset.from_form_values("Healer", Role.HEALER, values).stats.tenacity is None


@pytest.mark.parametrize(
    "name", [None, "", "   ", "x" * (MAX_GEARSET_NAME_LENGTH + 1)], ids=["none", "empty", "blank", "too-long"]
)
def test_invalid_names_are_rejected(name):
    """Reject missing, blank, and over-long names."""
    with pytest.raises(ValidationError):
        SavedGearset.from_form_values(name, Role.HEALER, _stats(Role.HEALER))


def test_name_is_stripped():
    """Strip surrounding whitespace from names."""
    assert _gearset("  Savage BiS  ").name == "Savage BiS"


def test_missing_stat_is_rejected():
    """Reject a form with an unfilled required stat."""
    values = _stats(Role.HEALER)
    values[Stats.CRITICAL_HIT] = None

    with pytest.raises(ValidationError):
        SavedGearset.from_form_values("Set", Role.HEALER, values)


def test_invalid_id_is_rejected():
    """Reject IDs that are not UUIDs."""
    with pytest.raises(ValidationError):
        SavedGearset.from_form_values("Set", Role.HEALER, _stats(Role.HEALER), gearset_id="not-a-uuid")


def test_to_internal_build_preserves_name_role_and_stats():
    """Convert to the shared internal-build model without losing data."""
    gearset = _gearset("Tank set", Role.TANK)

    build = gearset.to_internal_build()

    assert build.build_provider is BuildProvider.INTERNAL
    assert (build.build_name, build.build_role, build.build_stats) == (gearset.name, Role.TANK, gearset.stats)


def test_duplicate_names_get_distinct_ids():
    """Allow duplicate names because identity is the ID."""
    library = GearsetLibrary().add(_gearset("Same")).add(_gearset("Same"))

    assert len({gearset.id for gearset in library.gearsets}) == 2


def test_add_enforces_size_limit():
    """Refuse to add beyond the maximum library size."""
    with pytest.raises(GearsetLimitError):
        _library(MAX_SAVED_GEARSETS).add(_gearset("One too many"))


def test_library_rejects_oversized_stored_data():
    """Reject stored data that exceeds the size limit."""
    data = _library(MAX_SAVED_GEARSETS).model_dump(mode="json")
    data["gearsets"].append(_gearset("Extra").model_dump(mode="json"))

    with pytest.raises(ValidationError):
        GearsetLibrary.model_validate(data)


def test_library_rejects_duplicate_ids():
    """Reject stored data with repeated IDs."""
    gearset = _gearset()

    with pytest.raises(ValidationError):
        GearsetLibrary(gearsets=(gearset, gearset))


def test_library_rejects_dangling_default():
    """Reject a default ID that matches no gearset."""
    with pytest.raises(ValidationError):
        GearsetLibrary(default_id="11111111-1111-4111-8111-111111111111")


def test_replace_keeps_position_and_default():
    """Replace in place so ordering and the default are unaffected."""
    library = _library(3)
    target = library.gearsets[1]
    library = library.with_default(target.id)
    replacement = SavedGearset.from_form_values(target.name, Role.TANK, _stats(Role.TANK), gearset_id=target.id)

    updated = library.replace(replacement)

    assert [g.id for g in updated.gearsets] == [g.id for g in library.gearsets]
    assert updated.gearsets[1].role is Role.TANK
    assert updated.default_id == target.id


def test_replace_unknown_id_raises():
    """Raise a typed error when replacing a missing gearset."""
    with pytest.raises(GearsetNotFoundError):
        _library(1).replace(_gearset())


def test_remove_clears_default_when_default_is_removed():
    """Clear the default when its gearset is deleted."""
    library = _library(2)
    default = library.gearsets[0]

    updated = library.with_default(default.id).remove(default.id)

    assert updated.default_id is None
    assert [g.name for g in updated.gearsets] == ["Set 1"]


def test_remove_keeps_default_when_other_gearset_is_removed():
    """Keep the default pointing at the same gearset after earlier deletions."""
    library = _library(3)
    default = library.gearsets[2]

    updated = library.with_default(default.id).remove(library.gearsets[0].id)

    assert updated.default_id == default.id
    assert updated.default_gearset == default


def test_remove_unknown_id_raises():
    """Raise a typed error when deleting a missing gearset."""
    with pytest.raises(GearsetNotFoundError):
        _library(1).remove("11111111-1111-4111-8111-111111111111")


def test_with_default_sets_clears_and_validates():
    """Set, clear, and reject unknown defaults."""
    library = _library(2)
    target = library.gearsets[1]

    assert library.with_default(target.id).default_gearset == target
    assert library.with_default(target.id).with_default(None).default_gearset is None
    with pytest.raises(GearsetNotFoundError):
        library.with_default("11111111-1111-4111-8111-111111111111")


def test_library_operations_do_not_mutate_the_original():
    """Return new libraries and leave the original unchanged."""
    library = _library(1)

    library.add(_gearset("Another"))

    assert len(library.gearsets) == 1
