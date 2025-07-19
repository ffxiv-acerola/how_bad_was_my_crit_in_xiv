from unittest.mock import MagicMock, patch

import pytest
from dash.exceptions import PreventUpdate

with patch("dash.register_page"), patch("dash.get_app", return_value=MagicMock()):
    # Now it's safe to import the modules
    from crit_app.pages.party_analysis import party_fflogs_process


def compare_party_job_info(quick_build_data, party_accordion_children, job_information):
    """Assert that quick build table and party accordion reflect job information correctly.

    Args:
        quick_build_data (list): Quick build table data
        party_accordion_children (list): Party accordion children components
        job_information (list[dict]): Job information from fflogs
    """
    # Check that number of entries matches job information
    assert len(quick_build_data) == len(
        job_information
    ), "Quick build table data count does not match job information count"

    # We can't easily check the accordion children structure since it's complex
    # but we can verify it's not empty when job information is present
    assert len(party_accordion_children) > 0, "Party accordion should not be empty with valid job information"


@pytest.mark.parametrize(
    "mock_encounter_information, fflogs_url, expected_phase_options_length, expected_report_id",
    [
        (
            {"type": "multi_phase", "fight_id": 18, "encounter_name": "Sugar Riot", "encounter_id": 98},
            "https://www.fflogs.com/reports/3BgZa1FqCM6VLfvD?fight=18&type=damage-done",
            3,
            "3BgZa1FqCM6VLfvD",
        ),
        (
            {"type": "multi_phase", "fight_id": 18, "encounter_name": "Sugar Riot", "encounter_id": 98},
            "https://www.fflogs.com/reports/3BgZa1FqCM6VLfvD?fight=last&type=damage-done",
            3,
            "3BgZa1FqCM6VLfvD",
        ),
        (
            {"type": "multi_phase", "fight_id": 42, "encounter_name": "Howling Blade", "encounter_id": 100},
            "https://www.fflogs.com/reports/BVvWN7kwGAnFYyTD?fight=42&type=damage-done",
            3,
            "BVvWN7kwGAnFYyTD",
        ),
    ],
    indirect=["mock_encounter_information"],
)
def test_party_fflogs_process_correct_input(
    mock_encounter_information, fflogs_url, expected_phase_options_length, expected_report_id, monkeypatch
):
    """Test processing of fflogs URL with correct input for party analysis."""

    # Test data
    fflogs_data = None
    n_clicks = 1

    # Mock the encounter_information function to return our fixture data
    monkeypatch.setattr("crit_app.pages.party_analysis.encounter_information", lambda *args: mock_encounter_information)

    # Mock update_encounter_table to do nothing
    monkeypatch.setattr("crit_app.pages.party_analysis.update_encounter_table", lambda *args: None)
    monkeypatch.setattr(
        "crit_app.pages.party_analysis.create_quick_build_table_data",
        lambda *args: [{"job_build_url": ""}] * len(mock_encounter_information[4]),
    )
    monkeypatch.setattr(
        "crit_app.pages.party_analysis.create_party_accordion_children",
        lambda *args: [{"key": "value"}] * len(mock_encounter_information[4]),
    )

    # Extract the expected values from the mocked data
    expected_fight_id = mock_encounter_information[1]
    expected_encounter_name = mock_encounter_information[7]

    # Call the function
    result = party_fflogs_process(n_clicks, fflogs_url, fflogs_data)

    # Extract the relevant parts of the result
    feedback = result[0]
    encounter_name = result[3]
    phase_select_options = result[5]
    phase_select_hidden = result[6]
    quick_build_table = result[7]
    party_accordion_children = result[8]
    party_fflogs_hidden_div = result[9]
    fflogs_party_encounter = result[10]

    # Assertions
    assert feedback == [], "There should be no feedback for valid input"
    assert expected_encounter_name == encounter_name, f"Encounter name should be '{expected_encounter_name}'"
    assert (
        len(phase_select_options) == expected_phase_options_length
    ), f"Expected {expected_phase_options_length} phase options"

    # Check visibility of phase selector based on phase count
    expected_phase_hidden = True if len(phase_select_options) == 1 else False
    assert phase_select_hidden == expected_phase_hidden, "Phase selector visibility is incorrect"

    # Check that the fflogs data was properly extracted
    assert fflogs_party_encounter == {"fight_id": expected_fight_id, "report_id": expected_report_id}

    # Verify the party data is present
    job_information = mock_encounter_information[4]
    compare_party_job_info(quick_build_table, party_accordion_children, job_information)

    # Verify the FFLogs div is visible
    assert party_fflogs_hidden_div is False, "Party FFLogs div should be visible"


# Test for URL is None
def test_party_fflogs_process_none_url():
    """Test that PreventUpdate is raised when URL is None."""
    # Import inside the test to allow for mocking
    with patch("dash.register_page"):
        from crit_app.pages.party_analysis import party_fflogs_process

    n_clicks = 1
    url = None
    fflogs_data = None

    with pytest.raises(PreventUpdate):
        party_fflogs_process(n_clicks, url, fflogs_data)


@pytest.mark.parametrize(
    "error_code, url",
    [
        (0, "https://www.example.com/reports/abc123"),
        (1, "https://www.fflogs.com/reports/abc123"),
        (2, "https://www.fflogs.com/something-else"),
    ],
)
def test_party_fflogs_process_parse_errors(error_code, url, monkeypatch):
    """Test handling of URL parsing errors using FFLOGS_ERROR_MAPPING."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.party_analysis import party_fflogs_process
        from crit_app.util.api.fflogs import FFLOGS_ERROR_MAPPING

    # Test data
    n_clicks = 1
    fflogs_data = None

    # Get the expected error message from the mapping
    error_message = FFLOGS_ERROR_MAPPING[error_code]

    # Mock parse_fflogs_url to return an error
    monkeypatch.setattr("crit_app.pages.party_analysis.parse_fflogs_url", lambda *args: (None, None, error_message))

    # Call the function
    result = party_fflogs_process(n_clicks, url, fflogs_data)

    # First element should be the error message
    assert result[0] == error_message, f"Expected error message: {error_message}"
    # URL should be marked as invalid
    assert result[1] is False, "URL should be marked as invalid"
    assert result[2] is True, "URL should be marked as invalid"


@pytest.mark.parametrize(
    "error_message",
    [
        "Linked report is private/no longer available.",
        "fight=42 does not exist",
        "Some other API error",
    ],
)
def test_party_fflogs_process_encounter_info_errors(error_message, monkeypatch):
    """Test handling of encounter_information errors."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.party_analysis import party_fflogs_process

    # Test data
    n_clicks = 1
    url = "https://www.fflogs.com/reports/abc123?fight=42"
    fflogs_data = None

    # Mock parse_fflogs_url to return valid data
    monkeypatch.setattr("crit_app.pages.party_analysis.parse_fflogs_url", lambda *args: ("abc123", 42, ""))

    # Mock encounter_information to return an error
    mock_error_return = (error_message, None, None, None, None, None, None, None, None, None, None)
    monkeypatch.setattr("crit_app.pages.party_analysis.encounter_information", lambda *args: mock_error_return)

    # Call the function
    result = party_fflogs_process(n_clicks, url, fflogs_data)

    # First element should be the error message
    assert result[0] == error_message, "Error message should be returned"
    # URL should be marked as invalid
    assert result[1] is False, "URL should be marked as invalid"
    assert result[2] is True, "URL should be marked as invalid"


@pytest.mark.parametrize(
    "mock_encounter_information",
    [
        {"type": "single_phase", "encounter_id": -1, "encounter_name": "Unsupported Encounter"},
    ],
    indirect=True,
)
def test_party_fflogs_process_unsupported_encounter(mock_encounter_information, monkeypatch):
    """Test handling of unsupported encounter IDs."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.party_analysis import party_fflogs_process

    # Test data
    n_clicks = 1
    url = "https://www.fflogs.com/reports/abc123?fight=42"
    fflogs_data = None

    # Mock parse_fflogs_url to return valid data
    monkeypatch.setattr("crit_app.pages.party_analysis.parse_fflogs_url", lambda *args: ("abc123", -1, ""))

    # Mock encounter_information to return our fixture data
    monkeypatch.setattr("crit_app.pages.party_analysis.encounter_information", lambda *args: mock_encounter_information)

    # Call the function
    result = party_fflogs_process(n_clicks, url, fflogs_data)

    # First element should contain feedback about unsupported encounter
    assert "Sorry," in result[0], "Should show unsupported encounter message"
    assert mock_encounter_information[7] in result[0], f"Should mention encounter name {mock_encounter_information[7]}"

    # URL should be marked as invalid
    assert result[1] is False, "URL should be marked as invalid"
    assert result[2] is True, "URL should be marked as invalid"
