"""Convert a ``GearsetLibrary`` to and from its browser-store representation."""

from typing import Any

from pydantic import ValidationError

from crit_app_v2.gearsets.models import GearsetLibrary


def library_to_storage(library: GearsetLibrary) -> dict[str, Any]:
    """Serialize a library for a ``dcc.Store``.

    Parameters
    ----------
    library
        Library to serialize.

    Returns
    -------
    dict[str, Any]
        JSON-compatible data that ``library_from_storage`` accepts.
    """
    return library.model_dump(mode="json")


def library_from_storage(data: object) -> GearsetLibrary | None:
    """Validate stored data as a library.

    Parameters
    ----------
    data
        Value read from the browser store; may be missing or corrupted.

    Returns
    -------
    GearsetLibrary | None
        The validated library, or ``None`` when ``data`` is absent or invalid.
    """
    if data is None:
        return None
    try:
        return GearsetLibrary.model_validate(data)
    except ValidationError:
        return None
