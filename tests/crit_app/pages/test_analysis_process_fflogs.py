from unittest.mock import patch

import pytest


def compare_job_info_and_role_elements(radio_items: list[dict], job_information: list[dict], role: str):
    """Assert that the length of a role radio items list matches the number of jobs in that role from job_information.

    Args:
        radio_items (list[dict]): Role radio item list
        job_information (list[dict]): Job information from fflogs
        role (str): Role to test.
    """
    filtered_job_information = [j for j in job_information if j["role"] == role]

    assert len(filtered_job_information) == len(
        radio_items
    ), f"{role} radio items does not match job information length"


@pytest.mark.parametrize(
    "mock_encounter_information, fflogs_url, role, expected_phase_options_length, expected_report_id",
    [
        (
            {"type": "single_phase", "fight_id": 18, "encounter_name": "Sugar Riot", "encounter_id": 98},
            "https://www.fflogs.com/reports/3BgZa1FqCM6VLfvD?fight=18&type=damage-done",
            "Healer",
            1,
            "3BgZa1FqCM6VLfvD",
        ),
        (
            {"type": "single_phase", "fight_id": 18, "encounter_name": "Sugar Riot", "encounter_id": 98},
            "https://www.fflogs.com/reports/3BgZa1FqCM6VLfvD?fight=last&type=damage-done",
            "Healer",
            1,
            "3BgZa1FqCM6VLfvD",
        ),
        (
            {"type": "multi_phase", "fight_id": 42, "encounter_name": "Howling Blade", "encounter_id": 100},
            "https://www.fflogs.com/reports/BVvWN7kwGAnFYyTD?fight=42&type=damage-done",
            "Healer",
            3,
            "BVvWN7kwGAnFYyTD",
        ),
    ],
    indirect=["mock_encounter_information"],
)
def test_process_fflogs_url_correct_input(
    mock_encounter_information, fflogs_url, role, expected_phase_options_length, expected_report_id, monkeypatch
):
    """Test processing of fflogs URL with correct input."""
    # Import inside the test to allow for mocking
    with patch("dash.register_page"):
        from crit_app.pages.analysis import process_fflogs_url

    # Test data
    fflogs_data = None
    n_clicks = 1

    # Mock the encounter_information function to return our fixture data
    monkeypatch.setattr("crit_app.pages.analysis.encounter_information", lambda *args: mock_encounter_information)

    # Mock update_encounter_table to do nothing
    monkeypatch.setattr("crit_app.pages.analysis.update_encounter_table", lambda *args: None)

    # Extract the expected values from the mocked data
    expected_fight_id = mock_encounter_information[1]
    expected_encounter_name = mock_encounter_information[7]
    expected_furthest_phase = mock_encounter_information[10]

    # Call the function
    result = process_fflogs_url(n_clicks, fflogs_url, role, fflogs_data)

    # Extract the relevant parts of the result
    feedback = result[0]
    encounter_name_time = result[1]
    phase_select_options = result[2]
    phase_select_hidden = result[3]
    select_job_text = result[4]
    tank_radio_items = result[5]
    tank_radio_value = result[6]
    healer_radio_items = result[7]
    healer_radio_value = result[8]
    melee_radio_items = result[9]
    melee_radio_value = result[10]
    physical_ranged_radio_items = result[11]
    physical_ranged_radio_value = result[12]
    magical_ranged_radio_items = result[13]
    magical_ranged_radio_value = result[14]
    valid_url = result[15]
    invalid_url = result[16]
    encounter_info_hidden = result[17]
    fflogs_encounter_data = result[18]

    # Assertions
    assert feedback == [], "There should be no feedback for valid input"
    assert expected_encounter_name in encounter_name_time, f"Encounter name should contain '{expected_encounter_name}'"
    assert valid_url is True, "URL should be marked as valid"
    assert invalid_url is False, "URL should not be marked as invalid"
    assert encounter_info_hidden is False, "Encounter info should not be hidden"
    assert select_job_text == "Please select a job:", "Job selection prompt should be displayed"

    # Check that the fflogs data was properly extracted
    assert fflogs_encounter_data == {"fight_id": expected_fight_id, "report_id": expected_report_id}

    # Check length of phase options based on the fixture phase data
    assert (
        len(phase_select_options) == expected_phase_options_length
    ), f"Expected {expected_phase_options_length} phase options for phase {expected_furthest_phase}"

    # Check visibility of phase selector based on phase count
    expected_phase_hidden = True if expected_encounter_name == "Sugar Riot" else False
    assert phase_select_hidden == expected_phase_hidden, "Phase selector visibility is incorrect"

    # Extract job_information from the fixture
    job_information = mock_encounter_information[4]

    # Test the radio items for each role
    compare_job_info_and_role_elements(tank_radio_items, job_information, "Tank")
    compare_job_info_and_role_elements(healer_radio_items, job_information, "Healer")
    compare_job_info_and_role_elements(melee_radio_items, job_information, "Melee")
    compare_job_info_and_role_elements(physical_ranged_radio_items, job_information, "Physical Ranged")
    compare_job_info_and_role_elements(magical_ranged_radio_items, job_information, "Magical Ranged")

    # Check that radio values are None initially
    assert tank_radio_value is None
    assert healer_radio_value is None
    assert melee_radio_value is None
    assert physical_ranged_radio_value is None
    assert magical_ranged_radio_value is None


# Test for URL is None
def test_process_fflogs_url_none_url():
    """Test that PreventUpdate is raised when URL is None."""
    # Import inside the test to allow for mocking
    with patch("dash.register_page"):
        from dash.exceptions import PreventUpdate

        from crit_app.pages.analysis import process_fflogs_url

    n_clicks = 1
    url = None
    role = "Healer"
    fflogs_data = None

    with pytest.raises(PreventUpdate):
        process_fflogs_url(n_clicks, url, role, fflogs_data)


@pytest.mark.parametrize(
    "error_code, url",
    [
        (0, "https://www.example.com/reports/abc123"),
        (1, "https://www.fflogs.com/reports/abc123"),
        (2, "https://www.fflogs.com/something-else"),
    ],
)
def test_process_fflogs_url_parse_errors(error_code, url, monkeypatch):
    """Test handling of URL parsing errors using FFLOGS_ERROR_MAPPING."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.analysis import process_fflogs_url
        from crit_app.util.api.fflogs import FFLOGS_ERROR_MAPPING

    # Test data
    n_clicks = 1
    role = "Healer"
    fflogs_data = None

    # Get the expected error message from the mapping
    error_message = FFLOGS_ERROR_MAPPING[error_code]

    # Mock parse_fflogs_url to return an error
    monkeypatch.setattr("crit_app.pages.analysis.parse_fflogs_url", lambda *args: (None, None, error_message))

    # Call the function
    result = process_fflogs_url(n_clicks, url, role, fflogs_data)

    # First element should be the error message
    assert result[0] == error_message, f"Expected error message: {error_message}"
    # URL should be marked as invalid
    assert result[15] is False, "URL should be marked as invalid"
    assert result[16] is True, "URL should be marked as invalid"
    # Encounter info should be hidden
    assert result[17] is True, "Encounter info should be hidden"


@pytest.mark.parametrize(
    "error_message",
    [
        "Linked report is private/no longer available.",
        "fight=42 does not exist",
        "Some other API error",
    ],
)
def test_process_fflogs_url_encounter_info_errors(error_message, monkeypatch):
    """Test handling of encounter_information errors."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.analysis import process_fflogs_url

    # Test data
    n_clicks = 1
    url = "https://www.fflogs.com/reports/abc123?fight=42"
    role = "Healer"
    fflogs_data = None

    # Mock parse_fflogs_url to return valid data
    monkeypatch.setattr("crit_app.pages.analysis.parse_fflogs_url", lambda *args: ("abc123", 42, ""))

    # Mock encounter_information to return an error
    mock_error_return = (error_message, None, None, None, None, None, None, None, None, None, None)
    monkeypatch.setattr("crit_app.pages.analysis.encounter_information", lambda *args: mock_error_return)

    # Call the function
    result = process_fflogs_url(n_clicks, url, role, fflogs_data)

    # First element should be the error message
    assert result[0] == error_message, "Error message should be returned"
    # URL should be marked as invalid
    assert result[15] is False, "URL should be marked as invalid"
    assert result[16] is True, "URL should be marked as invalid"
    # Encounter info should be hidden
    assert result[17] is True, "Encounter info should be hidden"


@pytest.mark.parametrize(
    "mock_encounter_information",
    [
        {"type": "single_phase", "encounter_id": -1, "encounter_name": "Unsupported Encounter"},
    ],
    indirect=True,
)
def test_process_fflogs_url_unsupported_encounter(mock_encounter_information, monkeypatch):
    """Test handling of unsupported encounter IDs."""
    # Import inside the test
    with patch("dash.register_page"):
        from crit_app.pages.analysis import process_fflogs_url

    # Test data
    n_clicks = 1
    url = "https://www.fflogs.com/reports/abc123?fight=42"
    role = "Healer"
    fflogs_data = None

    # Mock parse_fflogs_url to return valid data
    monkeypatch.setattr("crit_app.pages.analysis.parse_fflogs_url", lambda *args: ("abc123", 42, ""))

    # Mock encounter_information to return our fixture data
    monkeypatch.setattr("crit_app.pages.analysis.encounter_information", lambda *args: mock_encounter_information)

    # Call the function
    result = process_fflogs_url(n_clicks, url, role, fflogs_data)

    # First element should contain feedback about unsupported encounter
    assert "Sorry," in str(result[0]), "Should show unsupported encounter message"
    assert mock_encounter_information[7] in str(
        result[0]
    ), f"Should mention encounter name {mock_encounter_information[7]}"
    assert "supported encounters" in str(result[0]), "Should mention supported encounters"

    # URL should be marked as invalid
    assert result[15] is False, "URL should be marked as invalid"
    assert result[16] is True, "URL should be marked as invalid"
    # Encounter info should be hidden
    assert result[17] is True, "Encounter info should be hidden"
