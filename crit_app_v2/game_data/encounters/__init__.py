"""Framework-independent encounter reference data."""

from .exclusions import (
    EXCLUDED_ENEMY_ID_SPEC,
    ExcludedEnemyIDs,
    get_excluded_enemy_ids,
)
from .phases import ENCOUNTER_PHASES, EncounterPhases, PhaseOption, get_phase_options
from .specs import (
    ENCOUNTER_SPECS,
    ContentType,
    EncounterSpec,
    get_encounter_spec,
    is_party_analyzeable,
    is_player_analyzeable,
)

__all__ = [
    "ENCOUNTER_PHASES",
    "ENCOUNTER_SPECS",
    "EXCLUDED_ENEMY_ID_SPEC",
    "ContentType",
    "EncounterPhases",
    "EncounterSpec",
    "ExcludedEnemyIDs",
    "PhaseOption",
    "get_encounter_spec",
    "get_excluded_enemy_ids",
    "get_phase_options",
    "is_party_analyzeable",
    "is_player_analyzeable",
]
