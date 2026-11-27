"""Region identifiers and the current global-world-to-region mapping."""

from enum import StrEnum


class Region(StrEnum):
    """Formal region labels used by analytics and player-world reference data."""

    NORTH_AMERICA = "NA"
    EUROPE = "EU"
    JAPAN = "JP"
    OCEANIA = "OC"
    KOREA = "KR"
    CHINA = "CN"


class ServerRegion(StrEnum):
    """FFLogs compact region identifiers returned by the reports API."""

    NORTH_AMERICA = "NA"
    EUROPE = "EU"
    JAPAN = "JP"
    OCEANIA = "OC"
    KOREA = "KR"
    CHINA = "CN"

    @property
    def patch_region(self) -> "PatchRegion":
        """Return the patch-cadence group associated with this FFLogs region."""
        if self is ServerRegion.KOREA:
            return PatchRegion.KO
        if self is ServerRegion.CHINA:
            return PatchRegion.CN
        return PatchRegion.GLOBAL

    @property
    def analytics_region(self) -> Region:
        """Return the region label used by analytics summaries."""
        return Region(self.value)


class PatchRegion(StrEnum):
    """Patch cadence used for a server's balance and release dates."""

    GLOBAL = "global"
    KO = "ko"
    CN = "cn"


WORLD_REGIONS: dict[str, Region] = {
    # North America
    "Adamantoise": Region.NORTH_AMERICA,
    "Cactuar": Region.NORTH_AMERICA,
    "Faerie": Region.NORTH_AMERICA,
    "Gilgamesh": Region.NORTH_AMERICA,
    "Jenova": Region.NORTH_AMERICA,
    "Midgardsormr": Region.NORTH_AMERICA,
    "Sargatanas": Region.NORTH_AMERICA,
    "Siren": Region.NORTH_AMERICA,
    "Balmung": Region.NORTH_AMERICA,
    "Brynhildr": Region.NORTH_AMERICA,
    "Coeurl": Region.NORTH_AMERICA,
    "Diabolos": Region.NORTH_AMERICA,
    "Goblin": Region.NORTH_AMERICA,
    "Malboro": Region.NORTH_AMERICA,
    "Mateus": Region.NORTH_AMERICA,
    "Zalera": Region.NORTH_AMERICA,
    "Cuchulainn": Region.NORTH_AMERICA,
    "Golem": Region.NORTH_AMERICA,
    "Halicarnassus": Region.NORTH_AMERICA,
    "Kraken": Region.NORTH_AMERICA,
    "Maduin": Region.NORTH_AMERICA,
    "Marilith": Region.NORTH_AMERICA,
    "Rafflesia": Region.NORTH_AMERICA,
    "Seraph": Region.NORTH_AMERICA,
    "Behemoth": Region.NORTH_AMERICA,
    "Excalibur": Region.NORTH_AMERICA,
    "Exodus": Region.NORTH_AMERICA,
    "Famfrit": Region.NORTH_AMERICA,
    "Hyperion": Region.NORTH_AMERICA,
    "Lamia": Region.NORTH_AMERICA,
    "Leviathan": Region.NORTH_AMERICA,
    "Ultros": Region.NORTH_AMERICA,
    # Europe
    "Cerberus": Region.EUROPE,
    "Louisoix": Region.EUROPE,
    "Moogle": Region.EUROPE,
    "Omega": Region.EUROPE,
    "Phantom": Region.EUROPE,
    "Ragnarok": Region.EUROPE,
    "Sagittarius": Region.EUROPE,
    "Spriggan": Region.EUROPE,
    "Alpha": Region.EUROPE,
    "Lich": Region.EUROPE,
    "Odin": Region.EUROPE,
    "Phoenix": Region.EUROPE,
    "Raiden": Region.EUROPE,
    "Shiva": Region.EUROPE,
    "Twintania": Region.EUROPE,
    "Zodiark": Region.EUROPE,
    # Oceania
    "Bismarck": Region.OCEANIA,
    "Ravana": Region.OCEANIA,
    "Sephirot": Region.OCEANIA,
    "Sophia": Region.OCEANIA,
    "Zurvan": Region.OCEANIA,
    # Japan
    "Aegis": Region.JAPAN,
    "Atomos": Region.JAPAN,
    "Carbuncle": Region.JAPAN,
    "Garuda": Region.JAPAN,
    "Gungnir": Region.JAPAN,
    "Kujata": Region.JAPAN,
    "Ramuh": Region.JAPAN,
    "Tonberry": Region.JAPAN,
    "Typhon": Region.JAPAN,
    "Unicorn": Region.JAPAN,
    "Alexander": Region.JAPAN,
    "Bahamut": Region.JAPAN,
    "Durandal": Region.JAPAN,
    "Fenrir": Region.JAPAN,
    "Ifrit": Region.JAPAN,
    "Ridill": Region.JAPAN,
    "Tiamat": Region.JAPAN,
    "Ultima": Region.JAPAN,
    "Valefor": Region.JAPAN,
    "Yojimbo": Region.JAPAN,
    "Zeromus": Region.JAPAN,
    "Anima": Region.JAPAN,
    "Asura": Region.JAPAN,
    "Chocobo": Region.JAPAN,
    "Hades": Region.JAPAN,
    "Ixion": Region.JAPAN,
    "Masamune": Region.JAPAN,
    "Pandaemonium": Region.JAPAN,
    "Shinryu": Region.JAPAN,
    "Titan": Region.JAPAN,
    "Belias": Region.JAPAN,
    "Kaguya": Region.JAPAN,
}


def world_to_region(world: str) -> Region:
    """Resolve an FFLogs player world to its analytics region.

    Raises
    ------
    ValueError
        If the world is not present in the reference mapping.
    """
    try:
        return WORLD_REGIONS[world]
    except KeyError as error:
        raise ValueError(f"Unknown FFLogs player world: {world!r}.") from error
