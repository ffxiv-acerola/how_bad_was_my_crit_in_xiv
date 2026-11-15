"""Presentation messages for normalized FFLogs encounter errors."""

from crit_app_v2.fflogs_encounters.errors import FFLogsError, FFLogsErrorCategory


def fflogs_error_message(error: FFLogsError) -> str:
    """Return concise user-facing feedback for an FFLogs query failure.

    Parameters
    ----------
    error
        Normalized error raised by the FFLogs encounter domain.

    Returns
    -------
    str
        Safe presentation text that does not expose provider diagnostics.
    """
    if error.category is FFLogsErrorCategory.INVALID_URL:
        return (
            "Enter an FFLogs report link that includes a fight, "
            "such as ?fight=12 or ?fight=last."
        )

    if error.category is FFLogsErrorCategory.REPORT_UNAVAILABLE:
        return "This FFLogs report is private, unavailable, or no longer exists."

    if error.category is FFLogsErrorCategory.NO_FIGHTS:
        return "No fights were found in this FFLogs report."

    if error.category is FFLogsErrorCategory.REQUEST_REJECTED:
        return "FFLogs rejected the request. Check the report link and try again."

    if error.category is FFLogsErrorCategory.FFLOGS_UNAVAILABLE:
        if error.status_code == 429:
            return "FFLogs is receiving too many requests. Please try again later."
        return "Could not reach FFLogs. Please try again later."

    if error.category is FFLogsErrorCategory.QUERY_FAILED:
        return "FFLogs could not complete this query. Please try again later."

    return "FFLogs returned an unexpected response. Please try again later."
