"""Phase reference data and phase-option construction."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EncounterPhases:
    """Named phases for an encounter that supports phase-level analysis.

    Attributes
    ----------
    encounter_id
        FFLogs encounter ID.
    phase_names
        Phase labels in order; index 0 is phase 1.
    """

    encounter_id: int
    phase_names: tuple[str, ...]


@dataclass(frozen=True)
class PhaseOption:
    """A selectable analysis range.

    Attributes
    ----------
    value
        Phase number, where 0 means the entire fight.
    label
        Display label.
    """

    value: int
    label: str


ENCOUNTER_PHASES: dict[int, EncounterPhases] = {
    1079: EncounterPhases(
        1079,
        (
            "P1: Fatebreaker",
            "P2: Usurper of Frost",
            "P3: Oracle of Darkness",
            "P4: Enter the Dragon",
            "P5: Pandora",
        ),
    ),
    98: EncounterPhases(98, ("Phase 1", "Phase 2", "Phase 3")),
    99: EncounterPhases(99, ("Phase 1", "Phase 2", "Phase 3")),
    100: EncounterPhases(100, ("Phase 1", "Phase 2")),
}


def get_phase_options(
    encounter_id: int, last_phase_index: int | None
) -> list[PhaseOption]:
    """Build the phase choices for an encounter.

    Parameters
    ----------
    encounter_id
        FFLogs encounter ID.
    last_phase_index
        Furthest phase reached in the fight, or ``None`` if unknown.

    Returns
    -------
    list[PhaseOption]
        "Entire Fight" followed by phases 1 through the furthest phase reached.
        Only "Entire Fight" is returned for encounters without phase support.
    """
    options = [PhaseOption(0, "Entire Fight")]
    spec = ENCOUNTER_PHASES.get(encounter_id)
    if spec is None or not last_phase_index:
        return options

    reached = min(last_phase_index, len(spec.phase_names))
    options.extend(
        PhaseOption(index, spec.phase_names[index - 1])
        for index in range(1, reached + 1)
    )
    return options
