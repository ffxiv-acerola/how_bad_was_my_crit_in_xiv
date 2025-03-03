import json

import pytest

from crit_app.util.api.job_build import (
    ERROR_CODE_MAP,
    _extract_xiv_gear_set,
    _parse_and_validate_xiv_gear_url,
)

# Test cases
xiv_gear_url_1 = "https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b"
xiv_gear_url_2 = "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
xiv_gear_url_3 = (
    "https://xivgear.app/?page=sl%7Cff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=2"
)
xiv_gear_url_4 = "https://xivgear.app/?page=bis|sch|endwalker|anabaseios"
xiv_gear_url_5 = "https://invalidapp.com/?page=sl%7Cf9b260a9-650c-445a-b3eb-c56d8d968501&onlySetIndex=1"
xiv_gear_url_6 = "https://xivgear.app/?page=sl%7Cinvalid-uuid&onlySetIndex=1"
xiv_gear_url_7 = (
    "https://xivgear.app/?page=sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908&selectedIndex=3"
)


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
            "crit_app/util/api/tests/test_data/xiv_gear_test_data.json",
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
                1.0,
            ),
        ),
        (
            "crit_app/util/api/tests/test_data/xiv_gear_test_data_2.json",
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
                1.0,
            ),
        ),
        (
            "crit_app/util/api/tests/test_data/xiv_gear_test_data_3.json",
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
                1.0,
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
