"""Encounter metadata and analysis support lookups."""

from dataclasses import dataclass
from enum import StrEnum


class ContentType(StrEnum):
    """Categories of encounter content."""

    RAID = "Raid"
    EXTREME = "Extreme"
    ULTIMATE = "Ultimate"
    UNREAL = "Unreal"


@dataclass(frozen=True)
class EncounterSpec:
    """Reference data for an encounter that may be analyzed.

    Attributes
    ----------
    encounter_id
        FFLogs encounter ID.
    name
        Encounter name.
    short_name
        Short community name for the encounter.
    content_type
        Category of content the encounter belongs to.
    relevant_patch
        Patch range the encounter was relevant in, such as ``"7.2 - 7.3"``.
    level
        Level the encounter is played at.
    player_analyzeable
        Whether player analysis is allowed for the encounter.
    party_analyzeable
        Whether party analysis is allowed for the encounter.
    """

    encounter_id: int
    name: str
    short_name: str
    content_type: ContentType
    relevant_patch: str
    level: int
    player_analyzeable: bool = True
    party_analyzeable: bool = True


ENCOUNTER_SPECS: dict[int, EncounterSpec] = {
    88: EncounterSpec(
        encounter_id=88,
        name="Kokytos",
        short_name="p9s",
        content_type=ContentType.RAID,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    89: EncounterSpec(
        encounter_id=89,
        name="Pandaemonium",
        short_name="p10s",
        content_type=ContentType.RAID,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    90: EncounterSpec(
        encounter_id=90,
        name="Themis",
        short_name="p11s",
        content_type=ContentType.RAID,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    91: EncounterSpec(
        encounter_id=91,
        name="Athena",
        short_name="p12sp1",
        content_type=ContentType.RAID,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    92: EncounterSpec(
        encounter_id=92,
        name="Pallas Athena",
        short_name="p12sp2",
        content_type=ContentType.RAID,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    93: EncounterSpec(
        encounter_id=93,
        name="Black Cat",
        short_name="m1s",
        content_type=ContentType.RAID,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    94: EncounterSpec(
        encounter_id=94,
        name="Honey B. Lovely",
        short_name="m2s",
        content_type=ContentType.RAID,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    95: EncounterSpec(
        encounter_id=95,
        name="Brute Bomber",
        short_name="m3s",
        content_type=ContentType.RAID,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    96: EncounterSpec(
        encounter_id=96,
        name="Wicked Thunder",
        short_name="m4s",
        content_type=ContentType.RAID,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    97: EncounterSpec(
        encounter_id=97,
        name="Dancing Green",
        short_name="m5s",
        content_type=ContentType.RAID,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    98: EncounterSpec(
        encounter_id=98,
        name="Sugar Riot",
        short_name="m6s",
        content_type=ContentType.RAID,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    99: EncounterSpec(
        encounter_id=99,
        name="Brute Abominator",
        short_name="m7s",
        content_type=ContentType.RAID,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    100: EncounterSpec(
        encounter_id=100,
        name="Howling Blade",
        short_name="m8s",
        content_type=ContentType.RAID,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    101: EncounterSpec(
        encounter_id=101,
        name="Vamp Fatale",
        short_name="m9s",
        content_type=ContentType.RAID,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    102: EncounterSpec(
        encounter_id=102,
        name="Red Hot + Deep Blue",
        short_name="m10s",
        content_type=ContentType.RAID,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    103: EncounterSpec(
        encounter_id=103,
        name="The Tyrant",
        short_name="m11s",
        content_type=ContentType.RAID,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    104: EncounterSpec(
        encounter_id=104,
        name="Lindwurm",
        short_name="m12s",
        content_type=ContentType.RAID,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    105: EncounterSpec(
        encounter_id=105,
        name="Lindwurm II",
        short_name="m12sp2",
        content_type=ContentType.RAID,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    1069: EncounterSpec(
        encounter_id=1069,
        name="Golbez",
        short_name="EW EX6",
        content_type=ContentType.EXTREME,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    1070: EncounterSpec(
        encounter_id=1070,
        name="Zeromus",
        short_name="EW EX7",
        content_type=ContentType.EXTREME,
        relevant_patch="6.4 - 6.5",
        level=90,
    ),
    1072: EncounterSpec(
        encounter_id=1072,
        name="Zoraal Ja",
        short_name="DT EX2",
        content_type=ContentType.EXTREME,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    1078: EncounterSpec(
        encounter_id=1078,
        name="Queen Eternal",
        short_name="DT EX3",
        content_type=ContentType.EXTREME,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    1079: EncounterSpec(
        encounter_id=1079,
        name="Futures Rewritten",
        short_name="FRU",
        content_type=ContentType.ULTIMATE,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    1080: EncounterSpec(
        encounter_id=1080,
        name="Zelenia",
        short_name="DT EX4",
        content_type=ContentType.EXTREME,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    1081: EncounterSpec(
        encounter_id=1081,
        name="????",
        short_name="DT EX5",
        content_type=ContentType.EXTREME,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    1082: EncounterSpec(
        encounter_id=1082,
        name="Guardian Arkveld",
        short_name="Arkveld",
        content_type=ContentType.EXTREME,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    1083: EncounterSpec(
        encounter_id=1083,
        name="The Doomtrain",
        short_name="DT EX6",
        content_type=ContentType.EXTREME,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    1084: EncounterSpec(
        encounter_id=1084,
        name="Enuo",
        short_name="DT EX7",
        content_type=ContentType.EXTREME,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    1085: EncounterSpec(
        encounter_id=1085,
        name="Dancing Mad",
        short_name="DMU",
        content_type=ContentType.ULTIMATE,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    3009: EncounterSpec(
        encounter_id=3009,
        name="Byakko",
        short_name="Byakko",
        content_type=ContentType.UNREAL,
        relevant_patch="7.0 - 7.1",
        level=100,
    ),
    3010: EncounterSpec(
        encounter_id=3010,
        name="Suzaku",
        short_name="Suzaku",
        content_type=ContentType.UNREAL,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    3011: EncounterSpec(
        encounter_id=3011,
        name="Seiryu",
        short_name="Seiryu",
        content_type=ContentType.UNREAL,
        relevant_patch="7.2 - 7.3",
        level=100,
    ),
    3012: EncounterSpec(
        encounter_id=3012,
        name="Tsukuyomi",
        short_name="Tsukuyomi",
        content_type=ContentType.UNREAL,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
    3013: EncounterSpec(
        encounter_id=3013,
        name="Shinryu",
        short_name="Shinryu",
        content_type=ContentType.UNREAL,
        relevant_patch="7.4 - 7.5",
        level=100,
    ),
}


def get_encounter_spec(encounter_id: int) -> EncounterSpec | None:
    """Look up the spec for an encounter.

    Parameters
    ----------
    encounter_id
        FFLogs encounter ID.

    Returns
    -------
    EncounterSpec or None
        The spec, or ``None`` if the encounter is not supported.
    """
    return ENCOUNTER_SPECS.get(encounter_id)


def is_player_analyzeable(encounter_id: int) -> bool:
    """Return whether player analysis is allowed for an encounter.

    Encounters without a spec are not analyzeable.
    """
    spec = ENCOUNTER_SPECS.get(encounter_id)
    return spec is not None and spec.player_analyzeable


def is_party_analyzeable(encounter_id: int) -> bool:
    """Return whether party analysis is allowed for an encounter.

    Encounters without a spec are not analyzeable.
    """
    spec = ENCOUNTER_SPECS.get(encounter_id)
    return spec is not None and spec.party_analyzeable
