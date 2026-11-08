"""Validated URL and encounter data models for FFLogs reports."""

from enum import StrEnum
from typing import Literal, Self
from urllib.parse import parse_qs, urlparse

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, model_validator

from crit_app_v2.game_data import Job, Role


class FflogsErrors(StrEnum):
    """User-facing errors raised while validating an FFLogs encounter URL."""

    NON_FFLOGS_URL = "URL isn't fflogs"
    INCOMPLETE_URL = "A specific fight must be linked, ?fight={fightID} or ?fight=last."
    MISSING_REPORT_ID = "No report id found"


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
            raise ValueError(FflogsErrors.NON_FFLOGS_URL)

        # These raise ValueError if either part is invalid.
        self._parse_report_id()
        self._parse_fight_id()
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
        report_parts: list = [
            segment for segment in parsed_url.path.split("/") if segment
        ]

        if len(report_parts) != 2:
            raise ValueError(FflogsErrors.INCOMPLETE_URL)

        if report_parts[0] != "reports":
            raise ValueError(FflogsErrors.INCOMPLETE_URL)

        if len(report_parts[1]) != 16:
            raise ValueError(FflogsErrors.INCOMPLETE_URL)

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
                raise ValueError(FflogsErrors.INCOMPLETE_URL)
            # Allow fight=last
            if fight_list[0] == "last":
                return fight_list[0]

            # Need to remap generic error and log actual one
            fight_id = int(fight_list[0])
            return fight_id

        else:
            raise ValueError(FflogsErrors.INCOMPLETE_URL)

    @property
    def report_id(self) -> str:
        """Return the report code embedded in the URL."""
        return self._parse_report_id()

    @property
    def fight_id(self) -> int | Literal["last"]:
        """Return the requested fight ID embedded in the URL."""
        return self._parse_fight_id()


# API response validation

# last fight ID
# Encounter info
# Limit break events


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
    last_phase_index: int  # >=0
    kill_time: float  # >= 0
    excluded_enemy_ids: list[int] | None

    players: list[EncounterPersonnel]
    limit_break: EncounterPersonnel | None


if __name__ == "__main__":
    url = "https://www.fflogs.com/reports/GpW6qnBmTML1zZC4?fight=37&type=damage-done"
    encounter_url = EncounterUrl(build_url=AnyHttpUrl(url))
    print(encounter_url)
