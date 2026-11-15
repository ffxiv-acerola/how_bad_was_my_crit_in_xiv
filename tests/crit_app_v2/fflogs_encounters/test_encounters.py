"""Tests for FFLogs encounter API queries."""

from unittest.mock import Mock

import pytest
import requests

from crit_app_v2.fflogs_encounters.encounters import _query_last_fight_id
from crit_app_v2.fflogs_encounters.errors import FFLogsError, FFLogsErrorCategory


def test_query_last_fight_id_selects_latest_started_fight(monkeypatch):
    """Select the fight with the latest start time, not the list length."""
    response = Mock()
    response.json.return_value = {
        "data": {
            "reportData": {
                "report": {
                    "fights": [
                        {"id": 8, "startTime": 1000},
                        {"id": 13, "startTime": 8000},
                        {"id": 21, "startTime": 4000},
                    ]
                }
            }
        }
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("crit_app_v2.fflogs_encounters.client.requests.post", post)

    result = _query_last_fight_id("report-code")

    assert result == 13
    request_kwargs = post.call_args.kwargs
    assert request_kwargs["json"]["operationName"] == "LastFightID"
    assert request_kwargs["json"]["variables"] == {"code": "report-code"}
    assert "id" in request_kwargs["json"]["query"]
    assert "startTime" in request_kwargs["json"]["query"]
    assert request_kwargs["timeout"] == 30


def test_query_last_fight_id_breaks_start_time_ties_by_id(monkeypatch):
    """Choose the higher fight ID when start timestamps are equal."""
    response = Mock()
    response.json.return_value = {
        "data": {"reportData": {"report": {"fights": [{"id": 4, "startTime": 1000.0}, {"id": 5, "startTime": 1000}]}}}
    }
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(return_value=response),
    )

    assert _query_last_fight_id("report-code") == 5


@pytest.mark.parametrize(
    ("response_data", "expected_category"),
    [
        (
            {"data": {"reportData": {"report": {"fights": []}}}},
            FFLogsErrorCategory.NO_FIGHTS,
        ),
        (
            {"errors": [{"message": "You do not have permission to view this report."}]},
            FFLogsErrorCategory.REPORT_UNAVAILABLE,
        ),
        (
            {"data": {"reportData": {"report": {"fights": [{"id": "4"}]}}}},
            FFLogsErrorCategory.UNEXPECTED_RESPONSE,
        ),
        (
            {"data": {"reportData": {"report": None}}},
            FFLogsErrorCategory.REPORT_UNAVAILABLE,
        ),
        ({"errors": "malformed"}, FFLogsErrorCategory.UNEXPECTED_RESPONSE),
    ],
    ids=[
        "empty-report",
        "private-report",
        "invalid-fight",
        "missing-report",
        "malformed-errors",
    ],
)
def test_query_last_fight_id_raises_categorized_errors(monkeypatch, response_data, expected_category):
    """Classify GraphQL and validation failures from report responses."""
    response = Mock()
    response.json.return_value = response_data
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(return_value=response),
    )

    with pytest.raises(FFLogsError) as error:
        _query_last_fight_id("report-code")

    assert error.value.category is expected_category


def test_query_last_fight_id_prefers_graphql_errors_to_partial_data(monkeypatch):
    """Reject partial report data when FFLogs also returns GraphQL errors."""
    response = Mock()
    response.json.return_value = {
        "data": {"reportData": {"report": {"fights": [{"id": 4, "startTime": 1000}]}}},
        "errors": [{"message": "The report could not be fully loaded."}],
    }
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(return_value=response),
    )

    with pytest.raises(FFLogsError) as error:
        _query_last_fight_id("report-code")

    assert error.value.category is FFLogsErrorCategory.QUERY_FAILED
    assert error.value.detail == "The report could not be fully loaded."


@pytest.mark.parametrize(
    ("status_code", "expected_category"),
    [
        (400, FFLogsErrorCategory.REQUEST_REJECTED),
        (429, FFLogsErrorCategory.FFLOGS_UNAVAILABLE),
        (503, FFLogsErrorCategory.FFLOGS_UNAVAILABLE),
    ],
    ids=["bad-request", "rate-limited", "server-unavailable"],
)
def test_query_last_fight_id_classifies_http_errors(monkeypatch, status_code, expected_category):
    """Classify HTTP rejection and temporary service errors."""
    response = Mock()
    http_response = requests.Response()
    http_response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError("request failed", response=http_response)
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(return_value=response),
    )

    with pytest.raises(FFLogsError) as error:
        _query_last_fight_id("report-code")

    assert error.value.category is expected_category
    assert error.value.status_code == status_code


def test_query_last_fight_id_classifies_connection_errors(monkeypatch):
    """Classify connection failures as temporary FFLogs unavailability."""
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(side_effect=requests.Timeout("request timed out")),
    )

    with pytest.raises(FFLogsError) as error:
        _query_last_fight_id("report-code")

    assert error.value.category is FFLogsErrorCategory.FFLOGS_UNAVAILABLE


def test_query_last_fight_id_classifies_json_decode_errors(monkeypatch):
    """Classify malformed JSON as an unexpected FFLogs response."""
    response = Mock()
    response.json.side_effect = ValueError("invalid JSON")
    monkeypatch.setattr(
        "crit_app_v2.fflogs_encounters.client.requests.post",
        Mock(return_value=response),
    )

    with pytest.raises(FFLogsError) as error:
        _query_last_fight_id("report-code")

    assert error.value.category is FFLogsErrorCategory.UNEXPECTED_RESPONSE


def _encounter_report():
    """Minimal EncounterInfo report payload."""
    return {
        "fights": [
            {
                "name": "Boss",
                "encounterID": 98,
                "kill": True,
                "startTime": 0,
                "endTime": 60000,
                "combatTime": None,
                "lastPhase": 0,
                "friendlyPets": None,
                "enemyNPCs": None,
            }
        ],
        "playerDetails": {
            "data": {"playerDetails": {"tanks": [{"name": "A", "id": 3, "server": "S", "type": "Paladin"}]}}
        },
    }


def test_fetch_encounter_resolves_last_fight(monkeypatch):
    """Resolve fight=last and link the encounter to the resolved fight."""
    from crit_app_v2.fflogs_encounters import encounters

    reports = {
        "LastFightID": {"fights": [{"id": 7, "startTime": 5}]},
        "EncounterInfo": _encounter_report(),
    }
    calls = []

    def fake_query(query, variables, operation_name):
        calls.append((operation_name, variables))
        return reports[operation_name]

    monkeypatch.setattr(encounters, "query_report", fake_query)

    result = encounters.fetch_encounter("https://www.fflogs.com/reports/GpW6qnBmTML1zZC4?fight=last")

    assert result.fight_id_resolved == 7
    assert result.encounter_url.fight_id == 7
    assert calls[1][1]["id"] == 7
    assert result.kill_time == 60


def test_fetch_encounter_rejects_invalid_url():
    """Invalid URLs raise a typed INVALID_URL error without any request."""
    from crit_app_v2.fflogs_encounters import encounters

    with pytest.raises(FFLogsError) as exc_info:
        encounters.fetch_encounter("https://example.com/reports/abc?fight=1")

    assert exc_info.value.category is FFLogsErrorCategory.INVALID_URL
