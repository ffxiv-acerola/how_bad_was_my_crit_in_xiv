"""Tests for the shared FFLogs GraphQL client."""

from unittest.mock import Mock

from crit_app_v2.fflogs_encounters.client import query_report


def test_query_report_returns_report_and_sends_named_operation(monkeypatch):
    """Return the common report payload and send operation metadata."""
    report_data = {"fights": [], "startTime": 123}
    response = Mock()
    response.json.return_value = {"data": {"reportData": {"report": report_data}}}
    post = Mock(return_value=response)
    monkeypatch.setattr("crit_app_v2.fflogs_encounters.client.requests.post", post)

    result = query_report(
        "query Test($code: String!) { reportData { report(code: $code) { fights { id } } } }",
        variables={"code": "report-code"},
        operation_name="Test",
    )

    assert result == report_data
    request_kwargs = post.call_args.kwargs
    assert request_kwargs["json"]["operationName"] == "Test"
    assert request_kwargs["json"]["variables"] == {"code": "report-code"}
    assert request_kwargs["headers"]["Authorization"].startswith("Bearer ")
    assert request_kwargs["timeout"] == 30
