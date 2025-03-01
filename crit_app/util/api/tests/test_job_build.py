import pytest

from crit_app.util.api.job_build import _parse_and_validate_xiv_gear_url

# Test cases
xivgear_url_1 = "https://xivgear.app/?page=sl%7Ca8881f6f-9ab3-40cc-9931-7035021a3f1b"
# Decodes to "sl|a8881f6f-9ab3-40cc-9931-7035021a3f1b", valid UUID so error_code becomes 2, set_index default = 0

xivgear_url_2 = "https://xivgear.app/?page=bis%7Csch%7Cendwalker%7Canabaseios"
# Decodes to "bis|sch|endwalker|anabaseios", contains "bis" so returns joined value "bis/sch/endwalker/anabaseios"
# with error_code = 0 and set_index default = 0

xivgear_url_3 = (
    "https://xivgear.app/?page=sl%7Cff8e55a8-a598-4bf3-abdd-bb40b66fa908&onlySetIndex=2"
)
# Decodes to "sl|ff8e55a8-a598-4bf3-abdd-bb40b66fa908"; valid UUID so error_code becomes 2, set_index = 2

xivgear_url_4 = "https://xivgear.app/?page=bis|sch|endwalker|anabaseios"
# Same as xivgear_url_2 but with literal pipe characters; expected: error_code = 0, uuid_value = "bis/sch/endwalker/anabaseios", set_index = 0

# Failure: invalid netloc
xivgear_url_5 = "https://invalidapp.com/?page=sl%7Cf9b260a9-650c-445a-b3eb-c56d8d968501&onlySetIndex=1"
# Expected: error_code 1, None, 0

# Failure: invalid UUID in non-BIS URL
xivgear_url_6 = "https://xivgear.app/?page=sl%7Cinvalid-uuid&onlySetIndex=1"
# Decodes to "sl|invalid-uuid"; since "invalid-uuid" is not a valid UUID, expected: error_code 2, None, 1


@pytest.mark.parametrize(
    "input_url, expected",
    [
        (xivgear_url_1, (2, "a8881f6f-9ab3-40cc-9931-7035021a3f1b", 0)),
        (xivgear_url_2, (0, "bis/sch/endwalker/anabaseios", 0)),
        (xivgear_url_3, (2, "ff8e55a8-a598-4bf3-abdd-bb40b66fa908", 2)),
        (xivgear_url_4, (0, "bis/sch/endwalker/anabaseios", 0)),
        (xivgear_url_5, (1, None, 0)),
        (xivgear_url_6, (2, None, 1)),
    ],
)
def test_parse_and_validate_xiv_gear_url(input_url, expected):
    """
    Test _parse_and_validate_xiv_gear_url() with various URLs.

    The test verifies that:
      - For valid URLs with a 'page' parameter containing either a BIS-type build or a normal UUID
        build, the correct error code, gearset ID, and onlySetIndex are returned.
      - For URLs with an invalid domain (netloc), error code 1 is returned.
      - For a normal (non-BIS) URL with an invalid UUID, error code 2 is returned and gearset ID is None.
    """
    result = _parse_and_validate_xiv_gear_url(input_url)
    assert result == expected
