"""Validated URL and encounter data models for FFLogs reports."""

from enum import StrEnum
from typing import Literal, Self
from urllib.parse import parse_qs, urlparse

from pydantic import (
    AliasPath,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from crit_app_v2.game_data import Job, Role


class FFLogsErrors(StrEnum):
    """User-facing errors raised while validating an FFLogs encounter URL."""

    NON_FFLOGS_URL = "URL isn't fflogs"
    INCOMPLETE_URL = "A specific fight must be linked, ?fight={fightID} or ?fight=last."
    MISSING_REPORT_ID = "No report id found"


class FFLogsGraphQLError(BaseModel):
    """The message field used from an FFLogs GraphQL error."""

    message: str = "FFLogs query failed."


class FFLogsReport(BaseModel):
    """Validated report response.

    Extracts ``response_data["data"]["reportData"]["report"]`` and any
    top-level GraphQL errors.
    """

    report: dict[str, object] | None = Field(
        default=None,
        validation_alias=AliasPath("data", "reportData", "report"),
    )
    errors: list[FFLogsGraphQLError] = Field(default_factory=list)


class FFLogsFightList(BaseModel):
    """List of fights in the report, used to resolve ``fight=last``."""

    id: int
    start_time: float = Field(validation_alias="startTime")


class FFLogsFriendlyPets(BaseModel):
    """Mapping of pet IDs and their player owner's ID."""

    id: int | None
    pet_owner: int | None = Field(validation_alias="petOwner")


class FFLogsEnemyNPCs(BaseModel):
    """Mapping of enemy NPC game IDs and their FFLogs actor ID."""

    game_id: int | None = Field(validation_alias="gameID")
    id: int | None


class FFLogsPlayerDetail(BaseModel):
    """Player identity and job fields from a role-specific group."""

    name: str
    id: int
    server: str
    job: str = Field(validation_alias="type")


class FFLogsReportFightData(BaseModel):
    """Top-level data selection returned by the LastFightID operation."""

    fights: list[FFLogsFightList]


class FFLogsEncounterFight(BaseModel):
    """Fight metadata selected by the encounter-information query."""

    name: str
    encounter_id: int = Field(validation_alias="encounterID")
    kill: bool | None
    start_time: float = Field(validation_alias="startTime")
    end_time: float = Field(validation_alias="endTime")
    combat_time: float | None = Field(validation_alias="combatTime")
    last_phase: int | None = Field(validation_alias="lastPhase")
    friendly_pets: list[FFLogsFriendlyPets | None] | None = Field(
        validation_alias="friendlyPets"
    )
    enemy_npcs: list[FFLogsEnemyNPCs | None] | None = Field(
        validation_alias="enemyNPCs"
    )


class FFLogsPlayerDetails(BaseModel):
    """Players grouped by role in FFLogs ``playerDetails`` data."""

    dps: list[FFLogsPlayerDetail] | None = None
    healers: list[FFLogsPlayerDetail] | None = None
    tanks: list[FFLogsPlayerDetail] | None = None


class FFLogsEncounterReport(BaseModel):
    """Report data selected by the EncounterInfo operation."""

    fights: list[FFLogsEncounterFight]
    player_details: FFLogsPlayerDetails = Field(
        validation_alias=AliasPath("playerDetails", "data", "playerDetails")
    )


class EncounterUrl(BaseModel):
    """A validated FFLogs report URL with derived report and fight identifiers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    build_url: AnyHttpUrl

    @model_validator(mode="after")
    def validate_url(self) -> Self:
        """Ensure the URL uses an FFLogs host and identifies a report and fight.

        Returns
        -------
        Self
            The validated encounter URL model.

        Raises
        ------
        ValueError
            If the host, report path, or fight query is invalid.
        """
        hostname = urlparse(str(self.build_url)).hostname
        valid_domains = ("www", "de", "fr", "ja", "ko", "cn")
        valid_hosts = {f"{domain}.fflogs.com" for domain in valid_domains}

        if hostname not in valid_hosts:
            raise ValueError(FFLogsErrors.NON_FFLOGS_URL)

        # These raise ValueError if either part is invalid.
        _ = self._parse_report_id()
        _ = self._parse_fight_id()
        return self

    def _parse_report_id(self) -> str:
        """Extract the report code from the validated URL path.

        Returns
        -------
        str
            The 16-character FFLogs report code.

        Raises
        ------
        ValueError
            If the URL path is not a report path with a 16-character code.
        """
        parsed_url = urlparse(str(self.build_url))
        report_parts: list[str] = [
            segment for segment in parsed_url.path.split("/") if segment
        ]

        if len(report_parts) != 2:
            raise ValueError(FFLogsErrors.INCOMPLETE_URL)

        if report_parts[0] != "reports":
            raise ValueError(FFLogsErrors.INCOMPLETE_URL)

        if len(report_parts[1]) != 16:
            raise ValueError(FFLogsErrors.INCOMPLETE_URL)

        return report_parts[1]

    def _parse_fight_id(self) -> int | Literal["last"]:
        """Extract the numeric fight ID or ``"last"`` from the URL.

        The fragment form used by older FFLogs links is treated as a query.

        Returns
        -------
        int or "last"
            The requested fight identifier.

        Raises
        ------
        ValueError
            If the URL has no fight parameter or its value is not an integer
            or ``"last"``.
        """
        parsed_url = urlparse(str(self.build_url).replace("#", "?"))
        url_query = parse_qs(parsed_url.query)
        fight_list = url_query.get("fight")

        if fight_list is not None:
            # Check that something is actually there.
            if len(fight_list) == 0:
                raise ValueError(FFLogsErrors.INCOMPLETE_URL)
            # Allow fight=last
            if fight_list[0] == "last":
                return fight_list[0]

            # Need to remap generic error and log actual one
            fight_id = int(fight_list[0])
            return fight_id

        else:
            raise ValueError(FFLogsErrors.INCOMPLETE_URL)

    def with_fight_id(self, fight_id: int) -> "EncounterUrl":
        """Return a canonical URL for the same report and a specific fight.

        Query parameters other than the fight, and any fragment, are dropped.

        Parameters
        ----------
        fight_id
            Numeric fight ID to link.

        Returns
        -------
        EncounterUrl
            New URL using the same host and report with ``?fight={fight_id}``.
        """
        hostname = urlparse(str(self.build_url)).hostname
        return EncounterUrl(
            build_url=AnyHttpUrl(
                f"https://{hostname}/reports/{self._parse_report_id()}?fight={fight_id}"
            )
        )

    @computed_field
    @property
    def report_id(self) -> str:
        """Return the report code embedded in the URL."""
        return self._parse_report_id()

    @computed_field
    @property
    def fight_id(self) -> int | Literal["last"]:
        """Return the requested fight ID embedded in the URL."""
        return self._parse_fight_id()


class EncounterPersonnel(BaseModel):
    """Participant information associated with an encounter."""

    player_name: str
    player_server: str
    player_id: int
    pet_ids: list[int] | None
    job: Job
    role: Role


class Encounter(BaseModel):
    """Normalized FFLogs encounter data and its participant records."""

    encounter_url: EncounterUrl
    fight_id_resolved: int
    encounter_id: int
    encounter_name: str  # not concerning ourselves with localization
    last_phase_index: int | None  # >=0
    kill_time: float  # >= 0
    excluded_enemy_ids: list[int] | None

    players: list[EncounterPersonnel]
    limit_break: EncounterPersonnel | None

    def players_by_role(self) -> dict[Role, list[EncounterPersonnel]]:
        """Group players by role in a deterministic order.

        Returns
        -------
        dict[Role, list[EncounterPersonnel]]
            Every role in ``Role`` order, including empty ones, with players
            sorted by FFLogs player ID.
        """
        return {
            role: sorted(
                (player for player in self.players if player.role is role),
                key=lambda player: player.player_id,
            )
            for role in Role
        }


if __name__ == "__main__":
    url = "https://www.fflogs.com/reports/GpW6qnBmTML1zZC4?fight=37&type=damage-done"
    encounter_url = EncounterUrl(build_url=AnyHttpUrl(url))
    print(encounter_url)
