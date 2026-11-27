"""Send FFLogs GraphQL requests and validate their shared report envelope."""

from typing import cast

import requests
from pydantic import ValidationError

from crit_app.config import FFLOGS_TOKEN
from crit_app_v2.fflogs_encounters.errors import FFLogsError, FFLogsErrorCategory
from crit_app_v2.fflogs_encounters.models import FFLogsReport

_FFLOGS_API_URL = "https://www.fflogs.com/api/v2/client"


def fflogs_headers() -> dict[str, str]:
    """Return authorization headers for FFLogs client API requests."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FFLOGS_TOKEN}",
    }


def query_report(
    query: str,
    variables: dict[str, object],
    operation_name: str,
) -> dict[str, object]:
    """Execute a GraphQL query and return its validated report object.

    Parameters
    ----------
    query
        GraphQL operation document.
    variables
        Variables supplied to the operation.
    operation_name
        Name of the GraphQL operation.

    Returns
    -------
    dict[str, object]
        The report at ``data.reportData.report``.

    Raises
    ------
    FFLogsError
        If the request fails, FFLogs reports a GraphQL error, the report is
        unavailable, or the response does not match the expected envelope.
    """
    payload = {
        "query": query,
        "variables": variables,
        "operationName": operation_name,
    }
    headers = fflogs_headers()

    try:
        response = requests.post(
            url=_FFLOGS_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else None
        if status_code in (408, 429) or status_code is None or status_code >= 500:
            category = FFLogsErrorCategory.FFLOGS_UNAVAILABLE
        else:
            category = FFLogsErrorCategory.REQUEST_REJECTED
        raise FFLogsError(category, status_code=status_code) from error
    except requests.RequestException as error:
        raise FFLogsError(FFLogsErrorCategory.FFLOGS_UNAVAILABLE) from error

    try:
        response_data = cast(object, response.json())
    except (requests.RequestException, ValueError) as error:
        raise FFLogsError(
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
            detail="FFLogs response body was not valid JSON.",
        ) from error

    try:
        response_model = FFLogsReport.model_validate(response_data)
    except ValidationError as error:
        raise FFLogsError(
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
            detail="FFLogs response did not match the report envelope.",
        ) from error

    if response_model.errors:
        error_message = response_model.errors[0].message
        if error_message == "You do not have permission to view this report.":
            raise FFLogsError(
                FFLogsErrorCategory.REPORT_UNAVAILABLE,
                detail=error_message,
            )
        raise FFLogsError(
            FFLogsErrorCategory.QUERY_FAILED,
            detail=error_message,
        )

    if response_model.report is None:
        raise FFLogsError(FFLogsErrorCategory.REPORT_UNAVAILABLE)

    return response_model.report
