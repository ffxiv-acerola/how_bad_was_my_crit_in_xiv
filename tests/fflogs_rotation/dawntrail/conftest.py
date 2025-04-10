import json

import pytest

from fflogs_rotation.paladin import PaladinActions


@pytest.fixture
def mock_gql_query_integration(monkeypatch, request):
    """
    Mock gql_query to return different responses based on operation name.

    This fixture allows testing PaladinActions without actual API calls by
    providing mock responses tailored to different GraphQL operations.
    """
    file_path = request.param if hasattr(request, "param") else None
    with open(file_path, "r") as f:
        mock_responses = json.load(f)

    def mock_gql_query(self, headers, query, variables, operation_name):
        return mock_responses[operation_name]

    # Replace the gql_query method with our mock version
    monkeypatch.setattr(PaladinActions, "gql_query", mock_gql_query)
