"""Framework-independent saved-gearset models, operations, and persistence."""

from .errors import GearsetLibraryError, GearsetLimitError, GearsetNotFoundError
from .legacy import LegacyMigrationResult, migrate_legacy_gearsets
from .models import (
    MAX_GEARSET_NAME_LENGTH,
    MAX_SAVED_GEARSETS,
    GearsetLibrary,
    SavedGearset,
)
from .storage import library_from_storage, library_to_storage

__all__ = [
    "MAX_GEARSET_NAME_LENGTH",
    "MAX_SAVED_GEARSETS",
    "GearsetLibrary",
    "GearsetLibraryError",
    "GearsetLimitError",
    "GearsetNotFoundError",
    "LegacyMigrationResult",
    "SavedGearset",
    "library_from_storage",
    "library_to_storage",
    "migrate_legacy_gearsets",
]
