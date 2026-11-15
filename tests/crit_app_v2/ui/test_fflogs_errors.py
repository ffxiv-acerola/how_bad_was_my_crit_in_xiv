"""Tests for rendering normalized FFLogs errors."""

import pytest

from crit_app_v2.fflogs_encounters.errors import FFLogsError, FFLogsErrorCategory
from crit_app_v2.ui.fflogs_errors import fflogs_error_message


@pytest.mark.parametrize(
    ("category", "status_code", "expected"),
    [
        (
            FFLogsErrorCategory.REPORT_UNAVAILABLE,
            None,
            "This FFLogs report is private, unavailable, or no longer exists.",
        ),
        (
            FFLogsErrorCategory.NO_FIGHTS,
            None,
            "No fights were found in this FFLogs report.",
        ),
        (
            FFLogsErrorCategory.REQUEST_REJECTED,
            400,
            "FFLogs rejected the request. Check the report link and try again.",
        ),
        (
            FFLogsErrorCategory.FFLOGS_UNAVAILABLE,
            429,
            "FFLogs is receiving too many requests. Please try again later.",
        ),
        (
            FFLogsErrorCategory.FFLOGS_UNAVAILABLE,
            503,
            "Could not reach FFLogs. Please try again later.",
        ),
        (
            FFLogsErrorCategory.QUERY_FAILED,
            None,
            "FFLogs could not complete this query. Please try again later.",
        ),
        (
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
            None,
            "FFLogs returned an unexpected response. Please try again later.",
        ),
    ],
    ids=[
        "report-unavailable",
        "no-fights",
        "request-rejected",
        "rate-limited",
        "service-unavailable",
        "query-failed",
        "unexpected-response",
    ],
)
def test_fflogs_error_message_maps_categories_to_safe_copy(category, status_code, expected):
    """Map typed FFLogs errors to safe user-facing messages."""
    error = FFLogsError(category, status_code=status_code, detail="internal detail")

    assert fflogs_error_message(error) == expected
    assert error.detail not in fflogs_error_message(error)
