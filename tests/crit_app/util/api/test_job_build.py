import json
from unittest.mock import patch

import pytest

from crit_app.util.api.job_build import (
    ERROR_CODE_MAP,
    INVALID_BUILD_PROVIDER,
    _extract_xiv_gear_set,
    _parse_and_validate_etro_url,
    _parse_and_validate_xiv_gear_url,
    etro_build,
    job_build_provider,
    parse_build_uuid,
    reconstruct_job_build_url,
    xiv_gear_build,
)

# Test cases
xiv_gear_url_1 = "https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b"
xiv_gear_url_2 = "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
xiv_gear_url_3 = "https://xivgear.app/?page=sl%7Cff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=2"
xiv_gear_url_4 = "https://xivgear.app/?page=bis|sch|endwalker|anabaseios"
xiv_gear_url_5 = "https://invalidapp.com/?page=sl%7Cf9b260a9-650c-445a-b3eb-c56d8d968501&onlySetIndex=1"
xiv_gear_url_6 = "https://xivgear.app/?page=sl%7Cinvalid-uuid&onlySetIndex=1"
xiv_gear_url_7 = "https://xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=3"


@pytest.mark.parametrize(
    "input_url, expected",
    [
        (xiv_gear_url_1, ("", "a8881f6f-9ab3-40cc-9931-7035021a3f1b", -1)),
        (xiv_gear_url_2, ("", "bis/sch/endwalker/anabaseios", -1)),
        (xiv_gear_url_3, ("", "ff8e55a8-a598-4bf3-abdd-bb40b66fa908", 2)),
        (xiv_gear_url_4, ("", "bis/sch/endwalker/anabaseios", -1)),
        (xiv_gear_url_5, (ERROR_CODE_MAP[1], None, 0)),
        (xiv_gear_url_6, (ERROR_CODE_MAP[2], None, 1)),
        (xiv_gear_url_7, ("", "ff8e55a8-a598-4bf3-abdd-bb40b66fa908", 3)),
    ],
)
def test_parse_and_validate_xiv_gear_url(input_url, expected):
    """
    Test _parse_and_validate_xiv_gear_url() with various URLs.

    Test cases:
    - xiv_gear_url_1: "https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b"
      Decodes to "sl|a8881f6f-9ab3-40cc-9931-7035021a3f1b", valid UUID so error_code becomes 2, set_index default = 0

    - xiv_gear_url_2: "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
      Decodes to "bis|sch|endwalker|anabaseios", contains "bis" so returns joined value "bis/sch/endwalker/anabaseios"
      with error_code = 0 and set_index default = 0

    - xiv_gear_url_3: "https://xivgear.app/?page=sl%7Cff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=2"
      Decodes to "sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908"; valid UUID so error_code becomes 2, set_index = 2

    - xiv_gear_url_4: "https://xivgear.app/?page=bis|sch|endwalker|anabaseios"
      Same as xiv_gear_url_2 but with literal pipe characters; expected: error_code = 0, uuid_value = "bis/sch/endwalker/anabaseios", set_index = 0

    - xiv_gear_url_5: "https://invalidapp.com/?page=sl%7Cf9b260a9-650c-445a-b3eb-c56d8d968501&onlySetIndex=1"
      Failure: invalid netloc; expected: error_code 1, None, 0

    - xiv_gear_url_6: "https://xivgear.app/?page=sl%7Cinvalid-uuid&onlySetIndex=1"
      Decodes to "sl|invalid-uuid"; since "invalid-uuid" is not a valid UUID, expected: error_code 2, None, 1

    - xiv_gear_url_7: "https://xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=3"
      Decodes to "sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908"; valid UUID so error_code becomes 2, set_index = 3

    The test verifies that:
      - For valid URLs with a 'page' parameter containing either a BIS-type build or a normal UUID
        build, the correct error code, gearset ID, and onlySetIndex are returned.
      - For URLs with an invalid domain (netloc), error code 1 is returned.
      - For a normal (non-BIS) URL with an invalid UUID, error code 2 is returned and gearset ID is None.
    """
    result = _parse_and_validate_xiv_gear_url(input_url)
    assert result == expected


@pytest.mark.parametrize(
    "input_path, expected_build",
    [
        (
            "tests/crit_app/util/api/test_data/xiv_gear_test_data.json",
            (
                "BRD",
                "FRU + Chaotic BiS",
                "Physical Ranged",
                4886,
                2448,
                474,
                3177,
                1777,
                146,
                "None",
            ),
        ),
        (
            "tests/crit_app/util/api/test_data/xiv_gear_test_data_2.json",
            (
                "PCT",
                "2.50 FRU Weapon + Chaotic Legs",
                "Magical Ranged",
                4883,
                2585,
                420,
                3090,
                1781,
                146,
                "None",
            ),
        ),
        (
            "tests/crit_app/util/api/test_data/xiv_gear_test_data_3.json",
            (
                "DRK",
                "2.50 BiS Edenmorn",
                "Tank",
                4842,
                2310,
                420,
                3174,
                1524,
                146,
                868,
            ),
        ),
    ],
)
def test_extract_xiv_gear_set(input_path, expected_build):
    """Test XIV gear sets are properly extracted.

    In addition, the following is tested:

    - PCT build, tests that Caster -> Magical Ranged and wdMag is selected
    - BRD build, tests that Ranged -> Physical Ranged and wdPhys is selected
    - DRK build, tests wdPhys is selected and TEN properly extracted.

    Args:
        input_path (str): Path to test data
        expected_build (tuple): tuple of expected build data
    """
    with open(input_path, "r") as f:
        xiv_gear_response = json.load(f)

    extracted_build = _extract_xiv_gear_set(xiv_gear_response)
    assert extracted_build == expected_build


@pytest.mark.parametrize(
    "input_url, fallback_gearset, expected",
    [
        (xiv_gear_url_1, None, ("a8881f6f-9ab3-40cc-9931-7035021a3f1b", "xivgear.app")),
        (
            xiv_gear_url_1,
            2,
            ("a8881f6f-9ab3-40cc-9931-7035021a3f1b&selectedIndex=2", "xivgear.app"),
        ),
        (xiv_gear_url_2, None, ("bis/sch/endwalker/anabaseios", "xivgear.app")),
        (
            xiv_gear_url_3,
            None,
            ("ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=2", "xivgear.app"),
        ),
        (xiv_gear_url_4, None, ("bis/sch/endwalker/anabaseios", "xivgear.app")),
        (xiv_gear_url_5, None, (None, None)),
        (xiv_gear_url_6, None, (None, None)),
        (
            xiv_gear_url_7,
            None,
            ("ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=3", "xivgear.app"),
        ),
        (
            "https://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            None,
            ("db9c3700-7722-423a-a170-68c221d014b7", "etro.gg"),
        ),
        (
            "https://etro.gg/gearset/db9c370-7722-423a-a170-68c221d014b7",
            None,
            (None, None),
        ),
    ],
)
def test_parse_build_uuid(input_url, fallback_gearset, expected):
    parsed_build_info = parse_build_uuid(input_url, fallback_gearset)
    assert parsed_build_info == expected


@pytest.mark.parametrize(
    "build_id, provider, expected_url",
    [
        # From test_parse_build_uuid: (xiv_gear_url_1, None) -> ("a8881f6f-9ab3-40cc-9931-7035021a3f1b", "xivgear.app")
        (
            "a8881f6f-9ab3-40cc-9931-7035021a3f1b",
            "xivgear.app",
            "https://xivgear.app/?page=sl|a8881f6f-9ab3-40cc-9931-7035021a3f1b",
        ),
        # With fallback gearset => &onlySetIndex=2
        (
            "a8881f6f-9ab3-40cc-9931-7035021a3f1b&onlySetIndex=2",
            "xivgear.app",
            "https://xivgear.app/?page=sl|a8881f6f-9ab3-40cc-9931-7035021a3f1b&onlySetIndex=2",
        ),
        # BIS build
        (
            "bis/sch/endwalker/anabaseios",
            "xivgear.app",
            "https://xivgear.app/?page=bis|sch|endwalker|anabaseios",
        ),
        # Another normal build with setIndex
        (
            "ff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=3",
            "xivgear.app",
            "https://xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=3",
        ),
        # Etro
        (
            "db9c3700-7722-423a-a170-68c221d014b7",
            "etro.gg",
            "https://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7",
        ),
        # Cases where build_id or provider might be None
        (None, "xivgear.app", ""),
        ("invalid-id", None, ""),
        (None, None, ""),
    ],
)
def test_reconstruct_job_build_url(build_id, provider, expected_url):
    """
    Test reconstruct_job_build_url() using build_id and provider combinations.

    aligned with the parse_build_uuid test cases.

    If either build_id or provider is None, we expect to receive None or an error.
    Otherwise, the function should return a valid URL string.
    """
    url = reconstruct_job_build_url(build_id, provider)
    assert url == expected_url, f"Expected '{expected_url}', got '{url}'"


@pytest.mark.parametrize(
    "job_build_url, expected_result",
    [
        # Valid etro.gg URLs
        ("https://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7", (True, "etro.gg")),
        ("http://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7", (True, "etro.gg")),
        ("https://www.etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7", (True, "etro.gg")),
        # Valid xivgear.app URLs
        ("https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b", (True, "xivgear.app")),
        ("http://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios", (True, "xivgear.app")),
        ("https://www.xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908", (True, "xivgear.app")),
        # Invalid URLs (wrong domain)
        ("https://example.com/gearset/db9c3700-7722-423a-a170-68c221d014b7", (False, INVALID_BUILD_PROVIDER)),
        ("https://etro-fake.gg/gearset/db9c3700", (False, INVALID_BUILD_PROVIDER)),
        ("https://fake-xivgear.app/?page=sl|uuid", (False, INVALID_BUILD_PROVIDER)),
        # Malformed URLs that should throw exceptions but be caught
        ("not-a-url", (False, INVALID_BUILD_PROVIDER)),
        ("http://", (False, INVALID_BUILD_PROVIDER)),
        ("", (False, INVALID_BUILD_PROVIDER)),
        # Edge cases
        ("https://etro.gg", (True, "etro.gg")),  # No path
        ("https://xivgear.app", (True, "xivgear.app")),  # No query params
    ],
)
def test_job_build_provider(job_build_url, expected_result):
    """
    Test job_build_provider function to validate URLs.

    The function should:
    - Return (True, "etro.gg") for valid etro.gg URLs
    - Return (True, "xivgear.app") for valid xivgear.app URLs
    - Return (False, error_message) for invalid domains
    - Handle exceptions gracefully for malformed URLs
    - Handle edge cases like URLs with no path or query parameters
    """
    result = job_build_provider(job_build_url)
    assert result == expected_result, f"For URL '{job_build_url}': expected {expected_result}, got {result}"


@pytest.mark.parametrize(
    "exception_type",
    [
        ValueError,
        AttributeError,
        TypeError,
        IndexError,
        KeyError,
        Exception,  # Generic exception
    ],
)
def test_job_build_provider_exception_handling(exception_type):
    """
    Test that job_build_provider properly handles exceptions during URL parsing.

    This test mocks urllib.parse.urlparse to raise various exceptions
    and verifies that the function:
    1. Catches the exception
    2. Returns (False, INVALID_BUILD_PROVIDER)
    """
    with patch("crit_app.util.api.job_build.urlparse", side_effect=exception_type("Test exception")):
        result = job_build_provider("https://etro.gg/test")
        assert result == (False, INVALID_BUILD_PROVIDER), f"Failed to handle {exception_type.__name__} properly"


@pytest.mark.parametrize(
    "etro_url, expected_result",
    [
        # Valid etro.gg URL with valid UUID
        (
            "https://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            ("db9c3700-7722-423a-a170-68c221d014b7", ""),
        ),
        # Valid etro.gg URL with invalid UUID format
        (
            "https://etro.gg/gearset/invalid-uuid-format",
            (None, ERROR_CODE_MAP[2]),
        ),
        # Valid etro.gg URL with malformed UUID
        (
            "https://etro.gg/gearset/db9c370-7722-423a-a170-68c221d014b7",
            (None, ERROR_CODE_MAP[2]),
        ),
        # URL with wrong domain
        (
            "https://example.com/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            (None, ERROR_CODE_MAP[1]),
        ),
        # URL with etro-like domain but not exact match
        (
            "https://fake-etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            (None, ERROR_CODE_MAP[1]),
        ),
        # URL with subdomain
        (
            "https://www.etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            ("db9c3700-7722-423a-a170-68c221d014b7", ""),
        ),
        # URL with different path format but valid UUID
        (
            "https://etro.gg/different-path/db9c3700-7722-423a-a170-68c221d014b7",
            ("db9c3700-7722-423a-a170-68c221d014b7", ""),
        ),
        # URL with extra segments in path
        (
            "https://etro.gg/extra/segments/gearset/db9c3700-7722-423a-a170-68c221d014b7",
            ("db9c3700-7722-423a-a170-68c221d014b7", ""),
        ),
        # URL with query parameters
        (
            "https://etro.gg/gearset/db9c3700-7722-423a-a170-68c221d014b7?param=value",
            ("db9c3700-7722-423a-a170-68c221d014b7", ""),
        ),
    ],
)
def test_parse_and_validate_etro_url(etro_url, expected_result):
    """
    Test _parse_and_validate_etro_url with various etro.gg URLs.

    The test covers:
    - Valid etro.gg URLs with valid UUIDs
    - Valid etro.gg URLs with invalid UUID format
    - Valid etro.gg URLs with malformed UUIDs
    - URLs with wrong domains
    - URLs with etro-like domains that don't exactly match
    - URLs with subdomains
    - URLs with different path formats
    - URLs with extra path segments
    - URLs with query parameters
    """
    result = _parse_and_validate_etro_url(etro_url)
    assert result == expected_result, f"For URL '{etro_url}': expected {expected_result}, got {result}"


@pytest.mark.parametrize(
    "exception_type",
    [
        ValueError,
        AttributeError,
        TypeError,
        IndexError,
        KeyError,
        Exception,  # Generic exception
    ],
)
def test_parse_and_validate_etro_url_exception_handling(exception_type):
    """
    Test that _parse_and_validate_etro_url properly handles exceptions.

    This test mocks urllib.parse.urlparse to raise various exceptions
    and verifies that the function catches them and returns the appropriate error.
    """
    with patch("crit_app.util.api.job_build.urlparse", side_effect=exception_type("Test exception")):
        result = _parse_and_validate_etro_url("https://etro.gg/gearset/some-id")
        assert result == (None, ERROR_CODE_MAP[3]), f"Failed to handle {exception_type.__name__} properly"


@pytest.mark.parametrize(
    "test_scenario, mock_url_return, mock_query_return, expected_error",
    [
        # Invalid URL cases
        (
            "Invalid domain",
            (None, ERROR_CODE_MAP[1]),  # _parse_and_validate_etro_url returns error
            None,  # Not used in this scenario
            ERROR_CODE_MAP[1],  # Expected error message
        ),
        (
            "Invalid UUID format",
            (None, ERROR_CODE_MAP[2]),  # _parse_and_validate_etro_url returns error
            None,  # Not used in this scenario
            ERROR_CODE_MAP[2],  # Expected error message
        ),
        (
            "URL parsing error",
            (None, ERROR_CODE_MAP[3]),  # _parse_and_validate_etro_url returns error
            None,  # Not used in this scenario
            ERROR_CODE_MAP[3],  # Expected error message
        ),
        # API query errors
        (
            "API query failure",
            ("valid-uuid", ""),  # Valid URL parsing
            ("API error message", False),  # _query_etro_stats returns error
            "API error message",  # Expected error message
        ),
    ],
)
def test_etro_build_error_cases(test_scenario, mock_url_return, mock_query_return, expected_error):
    """
    Test all error cases in etro_build function.

    This test covers:
    1. Invalid URLs (wrong domain, invalid UUID, parsing errors)
    2. API query failures

    For each case, it verifies that:
    - The function returns False for success
    - The correct error message is returned
    - All other return values are None
    - The correct length of 15 elements in all return cases
    """
    with patch("crit_app.util.api.job_build._parse_and_validate_etro_url", return_value=mock_url_return):
        # Only set up the second mock if we're testing API errors
        if mock_url_return[1] == "":
            with patch("crit_app.util.api.job_build._query_etro_stats", return_value=mock_query_return):
                result = etro_build("https://etro.gg/some-test-url")

                # Check return format and values
                assert isinstance(result, tuple), "Result should be a tuple"
                assert len(result) == 15, "Result tuple should have 15 elements"

                # Check expected values
                assert result[0] is False, f"For {test_scenario}, success should be False"
                assert (
                    result[1] == expected_error
                ), f"For {test_scenario}, expected error '{expected_error}', got '{result[1]}'"

                # All other values should be None
                for i in range(2, 15):
                    assert result[i] is None, f"For {test_scenario}, result[{i}] should be None, got {result[i]}"
        else:
            result = etro_build("https://etro.gg/some-test-url")

            # Check return format and values
            assert isinstance(result, tuple), "Result should be a tuple"
            assert len(result) == 15, "Result tuple should have 15 elements"

            # Check expected values
            assert result[0] is False, f"For {test_scenario}, success should be False"
            assert (
                result[1] == expected_error
            ), f"For {test_scenario}, expected error '{expected_error}', got '{result[1]}'"

            # All other values should be None
            for i in range(2, 15):
                assert result[i] is None, f"For {test_scenario}, result[{i}] should be None, got {result[i]}"


@pytest.mark.parametrize(
    "test_scenario, mock_url_return, mock_query_return, require_sheet_selection, expected_error",
    [
        # Invalid URL cases
        (
            "Invalid domain",
            (ERROR_CODE_MAP[1], None, 0),  # _parse_and_validate_xiv_gear_url returns error
            None,  # Not used in this scenario
            False,  # require_sheet_selection
            ERROR_CODE_MAP[1],  # Expected error message
        ),
        (
            "Invalid UUID format",
            (ERROR_CODE_MAP[2], None, 0),  # _parse_and_validate_xiv_gear_url returns error
            None,  # Not used in this scenario
            False,  # require_sheet_selection
            ERROR_CODE_MAP[2],  # Expected error message
        ),
        (
            "URL parsing error",
            (ERROR_CODE_MAP[3], None, 0),  # _parse_and_validate_xiv_gear_url returns error
            None,  # Not used in this scenario
            False,  # require_sheet_selection
            ERROR_CODE_MAP[3],  # Expected error message
        ),
        # API query errors
        (
            "API query failure",
            ("", "valid-uuid", -1),  # Valid URL parsing
            ("API error message", None),  # _query_xiv_gear_sets returns error
            False,  # require_sheet_selection
            "API error message",  # Expected error message
        ),
        # Sheet selection required but not provided
        (
            "Sheet selection required",
            ("", "valid-uuid", -1),  # Valid URL, no gear index specified
            ("", [{"mock": "gear_set"}, {"mock": "gear_set2"}]),  # Valid API response with mock gear sets
            True,  # require_sheet_selection = True
            "A specific gear set must be linked, not the whole sheet.",  # Expected error
        ),
    ],
)
def test_xiv_gear_build_error_cases(
    test_scenario, mock_url_return, mock_query_return, require_sheet_selection, expected_error
):
    """
    Test all error cases in xiv_gear_build function.

    This test covers:
    1. Invalid URLs (wrong domain, invalid UUID, parsing errors)
    2. API query failures
    3. Sheet selection required but not provided

    For each case, it verifies that:
    - The function returns False for success
    - The correct error message is returned
    - All other return values are set correctly for the error case
    """
    with patch("crit_app.util.api.job_build._parse_and_validate_xiv_gear_url", return_value=mock_url_return):
        # Only set up the second mock if we're testing API errors or sheet selection
        if mock_url_return[0] == "":
            with patch("crit_app.util.api.job_build._query_xiv_gear_sets", return_value=mock_query_return):
                result = xiv_gear_build("https://xivgear.app/some-test-url", require_sheet_selection)

                # Check return format and values
                assert isinstance(result, tuple), "Result should be a tuple"
                assert len(result) == 15, f"Result tuple should have 15 elements for '{test_scenario}'"

                # For the sheet selection case and API errors
                if test_scenario == "Sheet selection required" or test_scenario == "API query failure":
                    # Check expected values
                    assert result[0] is False, f"For {test_scenario}, success should be False"
                    assert (
                        result[1] == expected_error
                    ), f"For {test_scenario}, expected error '{expected_error}', got '{result[1]}'"

                    # Check the UI flag values
                    assert result[2] is True, "gearset_div_hidden should be True"
                    assert result[3] is False, "Valid job build url should be False"
                    assert result[4] is True, "Invalid job build url should be True"
                    assert result[5] is None, "job-build-name-div should be None"

        else:
            with patch("crit_app.util.api.job_build._query_xiv_gear_sets", return_value=("", None)):
                # For URL parsing errors
                result = xiv_gear_build("https://xivgear.app/some-test-url", require_sheet_selection)

                # Check return format and values for URL validation errors
                assert isinstance(result, tuple), "Result should be a tuple"
                assert len(result) == 15, f"Result tuple should have 15 elements for '{test_scenario}'"

                # Check expected values
                assert result[0] is False, f"For {test_scenario}, success should be False"
                assert (
                    result[1] == expected_error
                ), f"For {test_scenario}, expected error '{expected_error}', got '{result[1]}'"

                # Check the remaining elements
                assert result[2] is True, "gearset_div_hidden should be True"
                assert result[3] is False, "Valid job build url should be False"
                assert result[4] is True, "Invalid job build url should be True"
