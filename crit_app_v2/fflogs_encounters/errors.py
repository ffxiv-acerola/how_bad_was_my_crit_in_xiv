"""Typed errors raised while querying FFLogs encounter data."""

from enum import StrEnum


class FFLogsErrorCategory(StrEnum):
    """Stable categories for FFLogs query failures."""

    INVALID_URL = "invalid_url"
    REPORT_UNAVAILABLE = "report_unavailable"
    NO_FIGHTS = "no_fights"
    REQUEST_REJECTED = "request_rejected"
    FFLOGS_UNAVAILABLE = "fflogs_unavailable"
    UNEXPECTED_RESPONSE = "unexpected_response"
    QUERY_FAILED = "query_failed"


class FFLogsError(Exception):
    """Normalized FFLogs failure safe to pass to presentation code.

    Parameters
    ----------
    category
        Stable application-level category for the failure.
    status_code
        HTTP status code when the failure came from an HTTP response.
    detail
        Internal diagnostic detail. Presentation code should use ``category``
        rather than showing this value directly.
    """

    category: FFLogsErrorCategory
    status_code: int | None
    detail: str | None

    def __init__(
        self,
        category: FFLogsErrorCategory,
        *,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.category = category
        self.status_code = status_code
        self.detail = detail
        super().__init__(category.value)
