"""Strict models for user-saved gearsets and the library that holds them."""

from collections.abc import Mapping
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from crit_app_v2.build_providers.models import InternalBuild, RoleBuildStatsModel
from crit_app_v2.game_data import ROLE_SPECS, STAT_INPUTS, Role, Stats
from crit_app_v2.gearsets.errors import GearsetLimitError, GearsetNotFoundError

MAX_SAVED_GEARSETS = 25
MAX_GEARSET_NAME_LENGTH = 60


def _new_gearset_id() -> str:
    """Generate a new random gearset ID.

    Returns
    -------
    str
        A canonical lowercase UUID string.
    """
    return str(uuid4())


class SavedGearset(BaseModel):
    """A named, complete role-level gearset saved by the user.

    The ID is the gearset's stable identity; names are labels and may repeat.
    Tenacity is required for Tanks and forbidden for every other role.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(default_factory=_new_gearset_id)
    name: str = Field(min_length=1, max_length=MAX_GEARSET_NAME_LENGTH)
    role: Role
    stats: RoleBuildStatsModel

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        """Normalize the ID and ensure it is a UUID.

        Parameters
        ----------
        value
            Candidate gearset ID.

        Returns
        -------
        str
            The canonical lowercase UUID string.

        Raises
        ------
        ValueError
            If the value is not a valid UUID.
        """
        return str(UUID(value))

    @model_validator(mode="after")
    def check_stats(self) -> Self:
        """Check stat ranges and the role's Tenacity requirement.

        Returns
        -------
        Self
            The validated gearset.

        Raises
        ------
        ValueError
            If a stat is outside its canonical range, a Tank lacks Tenacity,
            or a non-Tank provides it.
        """
        requires_tenacity = ROLE_SPECS[self.role].requires_tenacity
        for stat in Stats:
            value = getattr(self.stats, stat.value)
            if stat is Stats.TENACITY and not requires_tenacity:
                if value is not None:
                    raise ValueError(f"Tenacity is not valid for {self.role.value}.")
                continue
            if value is None:
                raise ValueError(f"{stat.value} is required for {self.role.value}.")
            stat_range = STAT_INPUTS[stat]
            if not stat_range.lower <= value <= stat_range.upper:
                raise ValueError(
                    f"{stat.value} must be between {stat_range.lower} - "
                    f"{stat_range.upper}."
                )
        return self

    @classmethod
    def from_form_values(
        cls,
        name: str | None,
        role: Role,
        stats: Mapping[Stats, int | None],
        gearset_id: str | None = None,
    ) -> Self:
        """Build a strict gearset from raw form values.

        Tenacity is omitted for roles that do not use it, so stale values in a
        hidden input never reach strict validation.

        Parameters
        ----------
        name
            Gearset label as typed by the user.
        role
            Selected combat role.
        stats
            Entered values keyed by statistic.
        gearset_id
            Existing ID to keep, or ``None`` to generate a new one.

        Returns
        -------
        SavedGearset
            The validated gearset.

        Raises
        ------
        pydantic.ValidationError
            If any value is missing, out of range, or role-invalid.
        """
        stat_values = {stat.value: stats.get(stat) for stat in Stats}
        if not ROLE_SPECS[role].requires_tenacity:
            stat_values[Stats.TENACITY.value] = None
        fields: dict[str, object] = {
            "name": name,
            "role": role,
            "stats": RoleBuildStatsModel.model_validate(stat_values),
        }
        if gearset_id is not None:
            fields["id"] = gearset_id
        return cls.model_validate(fields)

    def to_internal_build(self) -> InternalBuild:
        """Convert the gearset to the shared internal-build model.

        Returns
        -------
        InternalBuild
            Role-level build ready to be applied to the stat form.
        """
        return InternalBuild(
            build_role=self.role,
            build_name=self.name,
            build_stats=self.stats,
        )


class GearsetLibrary(BaseModel):
    """The user's saved gearsets and which one loads by default.

    The library is immutable: every operation returns a new library. Its
    invariants are at most ``MAX_SAVED_GEARSETS`` entries, unique IDs, and a
    ``default_id`` that is either ``None`` or refers to a saved gearset.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1] = 1
    gearsets: tuple[SavedGearset, ...] = ()
    default_id: str | None = None

    @model_validator(mode="after")
    def check_invariants(self) -> Self:
        """Check the size limit, ID uniqueness, and default reference.

        Returns
        -------
        Self
            The validated library.

        Raises
        ------
        ValueError
            If any library invariant is violated.
        """
        if len(self.gearsets) > MAX_SAVED_GEARSETS:
            raise ValueError(f"At most {MAX_SAVED_GEARSETS} gearsets can be saved.")
        ids = [gearset.id for gearset in self.gearsets]
        if len(set(ids)) != len(ids):
            raise ValueError("Gearset ids must be unique.")
        if self.default_id is not None and self.default_id not in ids:
            raise ValueError("default_id must refer to a saved gearset.")
        return self

    @property
    def default_gearset(self) -> SavedGearset | None:
        """Return the default gearset, or ``None`` when none is set."""
        if self.default_id is None:
            return None
        return self.get(self.default_id)

    def get(self, gearset_id: str | None) -> SavedGearset | None:
        """Look up a gearset by ID.

        Parameters
        ----------
        gearset_id
            ID to find; ``None`` never matches.

        Returns
        -------
        SavedGearset | None
            The matching gearset, or ``None`` when absent.
        """
        for gearset in self.gearsets:
            if gearset.id == gearset_id:
                return gearset
        return None

    def add(self, gearset: SavedGearset) -> Self:
        """Append a gearset.

        Parameters
        ----------
        gearset
            Gearset to add.

        Returns
        -------
        GearsetLibrary
            A new library including the gearset.

        Raises
        ------
        GearsetLimitError
            If the library is already full.
        """
        if len(self.gearsets) >= MAX_SAVED_GEARSETS:
            raise GearsetLimitError(MAX_SAVED_GEARSETS)
        return self._with(gearsets=(*self.gearsets, gearset))

    def replace(self, gearset: SavedGearset) -> Self:
        """Replace the gearset that has the same ID, keeping its position.

        Parameters
        ----------
        gearset
            Replacement gearset.

        Returns
        -------
        GearsetLibrary
            A new library with the gearset replaced.

        Raises
        ------
        GearsetNotFoundError
            If no saved gearset has the same ID.
        """
        if self.get(gearset.id) is None:
            raise GearsetNotFoundError(gearset.id)
        return self._with(
            gearsets=tuple(
                gearset if existing.id == gearset.id else existing
                for existing in self.gearsets
            )
        )

    def remove(self, gearset_id: str) -> Self:
        """Delete a gearset, clearing the default if it was the default.

        Parameters
        ----------
        gearset_id
            ID of the gearset to delete.

        Returns
        -------
        GearsetLibrary
            A new library without the gearset.

        Raises
        ------
        GearsetNotFoundError
            If no saved gearset has this ID.
        """
        if self.get(gearset_id) is None:
            raise GearsetNotFoundError(gearset_id)
        return self._with(
            gearsets=tuple(g for g in self.gearsets if g.id != gearset_id),
            default_id=None if self.default_id == gearset_id else self.default_id,
        )

    def with_default(self, gearset_id: str | None) -> Self:
        """Set or clear the default gearset.

        Parameters
        ----------
        gearset_id
            ID to make the default, or ``None`` for no default.

        Returns
        -------
        GearsetLibrary
            A new library with the default updated.

        Raises
        ------
        GearsetNotFoundError
            If a non-``None`` ID is not in the library.
        """
        if gearset_id is not None and self.get(gearset_id) is None:
            raise GearsetNotFoundError(gearset_id)
        return self._with(default_id=gearset_id)

    def _with(self, **changes: object) -> Self:
        """Create a validated copy of the library with some fields changed.

        Parameters
        ----------
        **changes
            Field values to override.

        Returns
        -------
        GearsetLibrary
            The new, validated library.
        """
        return type(self).model_validate({**self.model_dump(), **changes})
