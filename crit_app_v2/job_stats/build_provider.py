from dataclasses import dataclass
from enum import StrEnum


class BuildProvider(StrEnum):
    """Supported external build providers."""

    ETRO = "etro.gg"
    XIV_GEAR = "xivgear.app"


@dataclass(frozen=True)
class BuildSpec:
    build_provider: BuildProvider
    build_id: str
    build_index: int | None
