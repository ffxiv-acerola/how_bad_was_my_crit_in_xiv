import json

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from crit_app.util.api.fflogs import (
    FFLOGS_ERROR_MAPPING,
    _encounter_jobs_and_lb,
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
    assert fight_id == expected_fight_id, f"Expected: {expected_fight_id}, got: {fight_id}"


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
def test_parse_fflogs_url(input_url, expected_report_id, expected_fight_id, expected_error):
    """Test parse_fflogs_url across valid and invalid FFLogs URLs."""
    report_id, fight_id, err = parse_fflogs_url(input_url)
    assert report_id == expected_report_id, f"Report ID: expected {expected_report_id}, got {report_id}"
    assert fight_id == expected_fight_id, f"Fight ID: expected {expected_fight_id}, got {fight_id}"
    assert err == expected_error, f"Error: expected {expected_error!r}, got {err!r}"


# Provided mock responses
report_no_exist = {"errors": [{"message": "This report does not exist."}]}
private_report = {"errors": [{"message": "You do not have permission to view this report."}]}
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
        (private_report, "Linked report is private/no longer available."),
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
        "tests/crit_app/util/api/test_data/lb_filter_1.json",
        "tests/crit_app/util/api/test_data/lb_filter_2.json",
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

    assert_frame_equal(output.reset_index(drop=True), expected_output.reset_index(drop=True))


@pytest.mark.parametrize(
    "response_data, expected_jobs, expected_limit_break",
    [
        # Case 1: Normal party with no limit break
        (
            {
                "data": {
                    "reportData": {
                        "report": {
                            "playerDetails": {
                                "data": {
                                    "playerDetails": {
                                        "Tank": [{"name": "John Tank", "server": "Excalibur"}],
                                        "Healer": [{"name": "Jane Healer", "server": "Excalibur"}],
                                        "DPS": [{"name": "Bob DPS", "server": "Excalibur"}],
                                    }
                                }
                            },
                            "table": {
                                "data": {
                                    "entries": [
                                        {
                                            "name": "John Tank",
                                            "id": 1,
                                            "icon": "Paladin",
                                            "pets": [{"id": 101}],
                                        },
                                        {
                                            "name": "Jane Healer",
                                            "id": 2,
                                            "icon": "WhiteMage",
                                        },
                                        {
                                            "name": "Bob DPS",
                                            "id": 3,
                                            "icon": "Dragoon",
                                        },
                                    ]
                                }
                            },
                        }
                    }
                }
            },
            [
                {
                    "job": "Paladin",
                    "player_name": "John Tank",
                    "player_server": "Excalibur",
                    "player_id": 1,
                    "pet_ids": "[101]",
                    "role": "Tank",
                },
                {
                    "job": "WhiteMage",
                    "player_name": "Jane Healer",
                    "player_server": "Excalibur",
                    "player_id": 2,
                    "pet_ids": None,
                    "role": "Healer",
                },
                {
                    "job": "Dragoon",
                    "player_name": "Bob DPS",
                    "player_server": "Excalibur",
                    "player_id": 3,
                    "pet_ids": None,
                    "role": "Melee",
                },
            ],
            [],
        ),
        # Case 2: Party with limit break
        (
            {
                "data": {
                    "reportData": {
                        "report": {
                            "playerDetails": {
                                "data": {
                                    "playerDetails": {
                                        "Tank": [{"name": "John Tank", "server": "Excalibur"}],
                                        "DPS": [{"name": "Bob DPS", "server": "Excalibur"}],
                                    }
                                }
                            },
                            "table": {
                                "data": {
                                    "entries": [
                                        {
                                            "name": "John Tank",
                                            "id": 1,
                                            "icon": "Paladin",
                                        },
                                        {
                                            "name": "Bob DPS",
                                            "id": 2,
                                            "icon": "BlackMage",
                                        },
                                        {
                                            "name": "Limit Break",
                                            "id": 100,
                                            "icon": "LimitBreak",
                                        },
                                    ]
                                }
                            },
                        }
                    }
                }
            },
            [
                {
                    "job": "Paladin",
                    "player_name": "John Tank",
                    "player_server": "Excalibur",
                    "player_id": 1,
                    "pet_ids": None,
                    "role": "Tank",
                },
                {
                    "job": "BlackMage",
                    "player_name": "Bob DPS",
                    "player_server": "Excalibur",
                    "player_id": 2,
                    "pet_ids": None,
                    "role": "Magical Ranged",
                },
            ],
            [
                {
                    "job": "LimitBreak",
                    "player_name": "Limit Break",
                    "player_server": None,
                    "player_id": 100,
                    "pet_ids": None,
                    "role": "Limit Break",
                }
            ],
        ),
        # Case 3: Player with blank name (edge case)
        (
            {
                "data": {
                    "reportData": {
                        "report": {
                            "playerDetails": {
                                "data": {
                                    "playerDetails": {
                                        "DPS": [{"name": "Valid Player", "server": "Excalibur"}],
                                    }
                                }
                            },
                            "table": {
                                "data": {
                                    "entries": [
                                        {
                                            "name": "",
                                            "id": 1969,
                                            "icon": "Unknown",
                                        },
                                        {
                                            "name": "Valid Player",
                                            "id": 2,
                                            "icon": "Summoner",
                                        },
                                    ]
                                }
                            },
                        }
                    }
                }
            },
            [
                {
                    "job": "Summoner",
                    "player_name": "Valid Player",
                    "player_server": "Excalibur",
                    "player_id": 2,
                    "pet_ids": None,
                    "role": "Magical Ranged",
                }
            ],
            [],
        ),
        # Case 4: Complex case with pets, blank name, and limit break
        (
            {
                "data": {
                    "reportData": {
                        "report": {
                            "playerDetails": {
                                "data": {
                                    "playerDetails": {
                                        "DPS": [{"name": "Summoner Player", "server": "Sargatanas"}],
                                        "Tank": [{"name": "Main Tank", "server": "Sargatanas"}],
                                    }
                                }
                            },
                            "table": {
                                "data": {
                                    "entries": [
                                        {
                                            "name": "",
                                            "id": 1969,
                                            "icon": "Unknown",
                                        },
                                        {
                                            "name": "Summoner Player",
                                            "id": 10,
                                            "icon": "Summoner",
                                            "pets": [{"id": 501}, {"id": 502}],
                                        },
                                        {
                                            "name": "Main Tank",
                                            "id": 20,
                                            "icon": "Warrior",
                                        },
                                        {
                                            "name": "Limit Break",
                                            "id": 999,
                                            "icon": "LimitBreak",
                                            "pets": [{"id": 1001}],
                                        },
                                    ]
                                }
                            },
                        }
                    }
                }
            },
            [
                {
                    "job": "Summoner",
                    "player_name": "Summoner Player",
                    "player_server": "Sargatanas",
                    "player_id": 10,
                    "pet_ids": "[501, 502]",
                    "role": "Magical Ranged",
                },
                {
                    "job": "Warrior",
                    "player_name": "Main Tank",
                    "player_server": "Sargatanas",
                    "player_id": 20,
                    "pet_ids": None,
                    "role": "Tank",
                },
            ],
            [
                {
                    "job": "LimitBreak",
                    "player_name": "Limit Break",
                    "player_server": None,
                    "player_id": 999,
                    "pet_ids": "[1001]",
                    "role": "Limit Break",
                }
            ],
        ),
    ],
)
def test_encounter_jobs_and_lb(response_data, expected_jobs, expected_limit_break):
    """Test _encounter_jobs_and_lb function with various scenarios.

    Tests include:
    - Normal party with no limit break
    - Party with limit break
    - Player with blank name (edge case)
    - Complex case with pets, blank name, and limit break
    """
    jobs, limit_break = _encounter_jobs_and_lb(response_data)

    assert jobs == expected_jobs, f"Jobs mismatch: expected {expected_jobs}, got {jobs}"
    assert (
        limit_break == expected_limit_break
    ), f"Limit break mismatch: expected {expected_limit_break}, got {limit_break}"
