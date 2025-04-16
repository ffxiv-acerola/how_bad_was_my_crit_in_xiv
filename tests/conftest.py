import pytest

from fflogs_rotation.base import BuffQuery


@pytest.fixture
def mock_buff_query(monkeypatch):
    def mock_gql_query(*args, **kwargs):
        return {}

    monkeypatch.setattr(BuffQuery, "gql_query", mock_gql_query)

    def mock_report_start_time(*args, **kwargs):
        return 0

    monkeypatch.setattr(BuffQuery, "_get_report_start_time", mock_report_start_time)
