import json

import pytest

from fflogs_rotation.base import BuffQuery
from fflogs_rotation.rotation import ActionTable


@pytest.fixture
def mock_action_table_api_via_file(monkeypatch, request):
    # Combined mock for damage events from file
    file_path = request.param if hasattr(request, "param") else None
    with open(file_path, "r") as f:
        mock_responses = json.load(f)

    # Combined mock for fight information
    def mock_fight_information(*args, **kwargs):
        return mock_responses["fight-info"]

    monkeypatch.setattr(ActionTable, "_query_fight_information", mock_fight_information)

    # Combined mock for phase downtime
    def mock_downtime(*args, **kwargs):
        return mock_responses["downtime"]

    monkeypatch.setattr(ActionTable, "_fetch_phase_downtime", mock_downtime)

    def mock_damage_events(*args, **kwargs):
        return mock_responses["damage-events"]

    monkeypatch.setattr(ActionTable, "_query_damage_events", mock_damage_events)


@pytest.fixture
def mock_buff_query(monkeypatch):
    def mock_gql_query(*args, **kwargs):
        return {}

    monkeypatch.setattr(BuffQuery, "gql_query", mock_gql_query)

    def mock_report_start_time(*args, **kwargs):
        return 0

    monkeypatch.setattr(BuffQuery, "_get_report_start_time", mock_report_start_time)
