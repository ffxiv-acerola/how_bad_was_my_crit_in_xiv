"""Typed errors raised by saved-gearset library operations."""


class GearsetLibraryError(Exception):
    """Base class for saved-gearset library operation failures."""


class GearsetNotFoundError(GearsetLibraryError):
    """Raised when an operation references a gearset ID not in the library.

    Parameters
    ----------
    gearset_id
        The ID that could not be found.
    """

    def __init__(self, gearset_id: str) -> None:
        super().__init__(f"No saved gearset with id {gearset_id!r}.")
        self.gearset_id = gearset_id


class GearsetLimitError(GearsetLibraryError):
    """Raised when adding a gearset would exceed the library size limit.

    Parameters
    ----------
    limit
        Maximum number of gearsets a library may hold.
    """

    def __init__(self, limit: int) -> None:
        super().__init__(f"A library can hold at most {limit} saved gearsets.")
        self.limit = limit
