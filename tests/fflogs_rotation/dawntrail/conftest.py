import json

import pytest

from fflogs_rotation.dragoon import DragoonActions
from fflogs_rotation.monk import MonkActions
from fflogs_rotation.ninja import NinjaActions

# from fflogs_rotation.base import BaseJobActions
from fflogs_rotation.paladin import PaladinActions
from fflogs_rotation.reaper import ReaperActions
from fflogs_rotation.rotation import ActionTable
from fflogs_rotation.samurai import SamuraiActions
from fflogs_rotation.viper import ViperActions


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
def mock_gql_query_integration(monkeypatch, request):
    """
    Mock gql_query to return different responses based on operation name.

    This fixture allows testing without actual API calls by
    providing mock responses tailored to different GraphQL operations.
    """
    file_path = request.param if hasattr(request, "param") else None
    with open(file_path, "r") as f:
        mock_responses = json.load(f)

    def mock_gql_query(self, headers, query, variables, operation_name):
        return mock_responses[operation_name]

    # Replace the gql_query method for all job action classes
    job_action_classes = [
        PaladinActions,
        DragoonActions,
        MonkActions,
        NinjaActions,
        ReaperActions,
        SamuraiActions,
        ViperActions,
    ]

    for job_class in job_action_classes:
        monkeypatch.setattr(job_class, "gql_query", mock_gql_query)
