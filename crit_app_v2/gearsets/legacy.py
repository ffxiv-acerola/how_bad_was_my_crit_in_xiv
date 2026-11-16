"""Migrate gearsets saved by the legacy application into a ``GearsetLibrary``.

The legacy app stored a list of dicts (keyed by index, with ``is_selected``
flags and abbreviated stat names) in the ``saved-gearsets`` browser store, and
the default gearset's list index in ``default-gear-index``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from crit_app_v2.game_data import Role, Stats
from crit_app_v2.gearsets.models import (
    MAX_GEARSET_NAME_LENGTH,
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    SavedGearset,
)

LEGACY_STAT_KEYS: Mapping[Stats, str] = {
    Stats.MAIN_STAT: "main_stat",
    Stats.DETERMINATION: "determination",
    Stats.SPEED_STAT: "speed",
    Stats.CRITICAL_HIT: "crit",
    Stats.DIRECT_HIT: "direct_hit",
    Stats.WEAPON_DAMAGE: "weapon_damage",
    Stats.TENACITY: "tenacity",
}
_UNNAMED = "Unnamed"


@dataclass(frozen=True)
class LegacyMigrationResult:
    """Outcome of migrating legacy gearsets.

    Parameters
    ----------
    library
        Library containing every record that migrated successfully.
    skipped
        Number of legacy records dropped because they were malformed, invalid
        under the current stat rules, or beyond the library size limit.
    """

    library: GearsetLibrary
    skipped: int


def _legacy_name(raw_name: object) -> str:
    """Normalize a legacy gearset name.

    Parameters
    ----------
    raw_name
        The stored name, which may be missing or not a string.

    Returns
    -------
    str
        A stripped, length-limited name, or a placeholder when blank.
    """
    if not isinstance(raw_name, str):
        return _UNNAMED
    return raw_name.strip()[:MAX_GEARSET_NAME_LENGTH].strip() or _UNNAMED


def _legacy_default_index(raw_index: object) -> int | None:
    """Parse the legacy default index, which may be a string or empty.

    Parameters
    ----------
    raw_index
        Stored ``default-gear-index`` value.

    Returns
    -------
    int | None
        The index, or ``None`` when absent or unparsable.
    """
    if isinstance(raw_index, bool):
        return None
    if isinstance(raw_index, int):
        return raw_index
    if isinstance(raw_index, float) and raw_index.is_integer():
        return int(raw_index)
    if isinstance(raw_index, str):
        try:
            return int(raw_index.strip())
        except ValueError:
            return None
    return None


def _migrate_record(record: object) -> SavedGearset | None:
    """Convert one legacy record, or return ``None`` if it is unusable.

    Parameters
    ----------
    record
        A legacy gearset dict.

    Returns
    -------
    SavedGearset | None
        The validated gearset, or ``None`` when the record cannot be migrated.
    """
    if not isinstance(record, Mapping):
        return None
    stats: dict[Stats, Any] = {
        stat: record.get(legacy_key) for stat, legacy_key in LEGACY_STAT_KEYS.items()
    }
    try:
        role = Role(record.get("role"))
        return SavedGearset.from_form_values(
            _legacy_name(record.get("name")), role, stats
        )
    except (ValidationError, ValueError, TypeError):
        return None


def migrate_legacy_gearsets(
    saved_gearsets: object, default_gear_index: object
) -> LegacyMigrationResult:
    """Convert legacy browser-store data into a ``GearsetLibrary``.

    Migration is tolerant: unusable records are skipped and counted rather than
    failing the whole import. Order is preserved, and the legacy default index
    is resolved to the migrated gearset's new ID when that record survived.

    Parameters
    ----------
    saved_gearsets
        Value of the legacy ``saved-gearsets`` store.
    default_gear_index
        Value of the legacy ``default-gear-index`` store.

    Returns
    -------
    LegacyMigrationResult
        The migrated library and the number of skipped records.
    """
    if not isinstance(saved_gearsets, list):
        return LegacyMigrationResult(GearsetLibrary(), 0)

    migrated: list[SavedGearset] = []
    id_by_legacy_index: dict[int, str] = {}
    skipped = 0
    for legacy_index, record in enumerate(saved_gearsets):
        gearset = _migrate_record(record)
        if gearset is None or len(migrated) >= MAX_SAVED_GEARSETS:
            skipped += 1
            continue
        migrated.append(gearset)
        id_by_legacy_index[legacy_index] = gearset.id

    default_index = _legacy_default_index(default_gear_index)
    default_id = (
        id_by_legacy_index.get(default_index) if default_index is not None else None
    )
    library = GearsetLibrary(gearsets=tuple(migrated), default_id=default_id)
    return LegacyMigrationResult(library, skipped)
