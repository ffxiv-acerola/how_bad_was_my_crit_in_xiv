import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from crit_app.util.api.fflogs import (
    FFLOGS_ERROR_MAPPING,
    _encounter_query_error_messages,
    _encounter_query_fight_id_exists,
    _fflogs_fight_id,
    _fflogs_report_id,
    _filter_unpaired_and_overkill_events,
    parse_fflogs_url,
)


@pytest.mark.parametrize(
    "url_path, expected_id",
    [
        ("/reports/1234567890123456", "1234567890123456"),  # exactly 16 chars
        ("/reports/shortID", None),  # too short
        ("/reports/toolongID-1234567", None),  # longer than 16
        ("/foo/1234567890123456", None),  # missing 'reports'
        ("/reports/", None),  # no ID at all
    ],
)
def test_fflogs_report_id(url_path, expected_id):
    """Check if _fflogs_report_id successfully extracts a valid 16-char ID from the path."""
    report_id = _fflogs_report_id(url_path)
    assert report_id == expected_id, f"Expected: {expected_id}, got: {report_id}"


@pytest.mark.parametrize(
    "url_query, expected_fight_id",
    [
        # Basic numeric fight ID
        ({"fight": ["1"]}, 1),
        # 'last' fight
        ({"fight": ["last"]}, "last"),
        # invalid fight (not numeric, not 'last')
        ({"fight": ["abc"]}, None),
        # empty list or missing param
        ({}, None),
        ({"fight": []}, None),
    ],
)
def test_fflogs_fight_id(url_query, expected_fight_id):
    """Check whether _fflogs_fight_id extracts the fight ID correctly."""
    fight_id = _fflogs_fight_id(url_query)
    assert (
        fight_id == expected_fight_id
    ), f"Expected: {expected_fight_id}, got: {fight_id}"


@pytest.mark.parametrize(
    "input_url, expected_report_id, expected_fight_id, expected_error",
    [
        # Valid: domain, report ID, fight=last
        (
            "https://www.fflogs.com/reports/abcdefgh12345678?fight=last",
            "abcdefgh12345678",
            "last",
            "",
        ),
        # Valid: numeric fight ID
        (
            "https://www.fflogs.com/reports/abcdefgh12345678?fight=7",
            "abcdefgh12345678",
            7,
            "",
        ),
        # Wrong domain
        (
            "https://www.fake-logs.com/reports/abcdefgh12345678?fight=last",
            None,
            None,
            FFLOGS_ERROR_MAPPING[0],
        ),
        # Missing fight param
        (
            "https://www.fflogs.com/reports/abcdefgh12345678",
            None,
            None,
            FFLOGS_ERROR_MAPPING[1],
        ),
        # Invalid fight param
        (
            "https://www.fflogs.com/reports/abcdefgh12345678?fight=abc",
            None,
            None,
            FFLOGS_ERROR_MAPPING[1],
        ),
        # Invalid report ID length
        (
            "https://www.fflogs.com/reports/shortID?fight=3",
            None,
            None,
            FFLOGS_ERROR_MAPPING[2],
        ),
        # # replaced with ?
        (
            "https://www.fflogs.com/reports/abcdefgh12345678#fight=2",
            "abcdefgh12345678",
            2,
            "",
        ),
    ],
)
def test_parse_fflogs_url(
    input_url, expected_report_id, expected_fight_id, expected_error
):
    """Test parse_fflogs_url across valid and invalid FFLogs URLs."""
    report_id, fight_id, err = parse_fflogs_url(input_url)
    assert (
        report_id == expected_report_id
    ), f"Report ID: expected {expected_report_id}, got {report_id}"
    assert (
        fight_id == expected_fight_id
    ), f"Fight ID: expected {expected_fight_id}, got {fight_id}"
    assert err == expected_error, f"Error: expected {expected_error!r}, got {err!r}"


# Provided mock responses
report_no_exist = {"errors": [{"message": "This report does not exist."}]}
private_report = {
    "errors": [{"message": "You do not have permission to view this report."}]
}
nonexistent_fight_id = {
    "data": {
        "reportData": {
            "report": {
                "rankings": {"data": []},
                "fights": [],
                "playerDetails": {"data": {"playerDetails": []}},
            }
        }
    }
}
existent_fight_id = {
    "data": {
        "reportData": {
            "report": {
                "rankings": {"data": []},
                "fights": [
                    {
                        "encounterID": 0,
                        "kill": None,
                        "startTime": 84801,
                        "endTime": 97551,
                        "name": "Striking Dummy",
                    }
                ],
                "playerDetails": {"data": {"playerDetails": []}},
            }
        }
    }
}


def test_encounter_query_error_messages_no_error():
    response = {"data": {"some": "value"}}
    err = _encounter_query_error_messages(response)
    assert err == "", f"Expected no error message, got '{err}'"


@pytest.mark.parametrize(
    "response, expected_error",
    [
        (report_no_exist, "This report does not exist."),
        (private_report, "You do not have permission to view this report."),
    ],
)
def test_encounter_query_error_messages_with_errors(response, expected_error):
    err = _encounter_query_error_messages(response)
    assert err == expected_error, f"Expected '{expected_error}', got '{err}'"


@pytest.mark.parametrize(
    "response_dict, exists",
    [
        (nonexistent_fight_id, False),
        (existent_fight_id, True),
    ],
)
def test_encounter_query_fight_id_exists(response_dict, exists):
    result = _encounter_query_fight_id_exists(response_dict)
    assert result is exists, f"Expected {exists} for fight id existence, got {result}"


@pytest.mark.parametrize(
    "test_data_path",
    [
        "crit_app/util/api/tests/test_data/lb_filter_1.json",
        "crit_app/util/api/tests/test_data/lb_filter_2.json",
    ],
)
def test_filter_unpaired_and_overkill_events(test_data_path):
    """Test that overkill and unpaired lb events are correctly filtered out.

    Args:
        test_data_path (str): path to test data.
    """
    with open(test_data_path, "r") as f:
        test_data = json.load(f)

    input_df = pd.DataFrame(test_data["input"])

    expected_output = pd.DataFrame(test_data["output"])

    output = _filter_unpaired_and_overkill_events(input_df)

    assert_frame_equal(
        output.reset_index(drop=True), expected_output.reset_index(drop=True)
    )
