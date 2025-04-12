from unittest.mock import patch

import pytest
from dash import html
from dash.exceptions import PreventUpdate

# Mock dash.register_page at the module level, before importing
# This prevents the PageError during import
with patch("dash.register_page"):
    # Now it's safe to import the modules
    from crit_app.pages.analysis import (
        process_job_build_url,
    )


# Define a fixture for parameterization that allows getting different build responses
@pytest.fixture
def build_response(request):
    """Fixture that returns the specified build response based on the parameter."""
    build_type = request.param
    if build_type == "etro.gg":
        return (
            True,
            "",
            True,
            True,
            False,
            [html.H4("Build name: 2.50")],
            "Melee",
            3379,
            1870,
            400,
            2567,
            1396,
            132,
            "None",
            {"gear_index": -1, "data": []},
        )
    elif build_type == "xivgear.app":
        return (
            True,
            "",
            False,
            True,
            False,
            [html.H4("dsr nin tentative bis")],
            "Melee",
            2588,
            1829,
            514,
            2208,
            1353,
            120,
            "None",
            {
                "gear_index": 0,
                "data": [
                    (
                        "NIN",
                        "dsr nin tentative bis",
                        "Melee",
                        2588,
                        1829,
                        514,
                        2208,
                        1353,
                        120,
                        "None",
                    )
                ],
            },
        )


def test_process_job_build_url_none_clicks():
    """Test that process_job_build_url raises PreventUpdate when n_clicks is None."""
    with pytest.raises(PreventUpdate):
        process_job_build_url(None, "https://etro.gg/gearset/123456", "Melee")


@pytest.mark.parametrize(
    "url, provider, selected_role",
    [
        ("https://etro.gg/gearset/123456", "etro.gg", "Melee"),
        (
            "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501",
            "xivgear.app",
            "Tank",
        ),
        ("https://invalid-url.com/gearset/123456", "invalid", "Healer"),
    ],
)
def test_process_job_build_url_provider_detection(url, provider, selected_role, monkeypatch):
    """Test that process_job_build_url correctly identifies the provider."""
    # Mock job_build_provider to return our expected values
    if provider == "invalid":
        monkeypatch.setattr(
            "crit_app.pages.analysis.job_build_provider",
            lambda x: (False, "Only etro.gg or xivgear.app is supported."),
        )
        # For invalid URLs, we should get the error message in the feedback
        result = process_job_build_url(1, url, selected_role)
        assert result[0] == "Only etro.gg or xivgear.app is supported."
    else:
        monkeypatch.setattr("crit_app.pages.analysis.job_build_provider", lambda x: (True, provider))
        # For this test, we don't care about the actual build calls, just that the right one is chosen
        monkeypatch.setattr(
            "crit_app.pages.analysis.etro_build",
            lambda x: (
                False,
                "Mocked error",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )
        monkeypatch.setattr(
            "crit_app.pages.analysis.xiv_gear_build",
            lambda x: (
                False,
                "Mocked error",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )

        result = process_job_build_url(1, url, selected_role)
        assert result[0] == "Mocked error"


# List of test parameters for each provider
provider_params = [
    # (provider type, url, expected hide_xiv_gear_set_selector)
    ("etro.gg", "etro.gg", "https://etro.gg/gearset/123456", True),
    (
        "xivgear.app",
        "xivgear.app",
        "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501",
        False,
    ),
]


@pytest.mark.parametrize(
    "build_response, provider_type, url, expected_hidden",
    provider_params,
    indirect=["build_response"],
)
def test_process_job_build_url_with_provider(build_response, provider_type, url, expected_hidden, monkeypatch):
    """Test process_job_build_url with different providers using parameterization."""
    selected_role = "Melee"

    # Mock job_build_provider to return the appropriate provider
    monkeypatch.setattr(
        "crit_app.pages.analysis.job_build_provider",
        lambda x: (
            True,
            provider_type,
        ),
    )
    monkeypatch.setattr("crit_app.pages.analysis.etro_build", lambda x: build_response)
    monkeypatch.setattr("crit_app.pages.analysis.xiv_gear_build", lambda x: build_response)

    # Call the function
    result = process_job_build_url(1, url, selected_role)

    # Check that the output matches what we expect
    assert result[0] == []  # No feedback
    assert result[1] is expected_hidden  # Hidden xiv-gear-set-div
    assert result[2] is True  # Valid URL
    assert result[3] is False  # Not invalid URL
    assert result[4] == [build_response[5][0]]  # Build name
    assert result[5] == "Melee"  # Role

    # Check that stats are correctly loaded from the provider's response
    assert result[6] == build_response[7]  # Main stat
    assert result[7] == build_response[8]  # DET
    assert result[8] == build_response[9]  # Speed stat
    assert result[9] == build_response[10]  # CRT
    assert result[10] == build_response[11]  # DH
    assert result[11] == build_response[12]  # WD
    assert result[12] == build_response[13]  # TEN

    # Check sheet data
    if provider_type == "etro.gg":
        assert result[13] == {
            "gear_index": -1,
            "data": [],
        }  # Sheet data for etro is empty
    else:
        assert result[13]["gear_index"] == 0  # xivgear has a valid gear index
        assert len(result[13]["data"]) > 0  # xivgear has data


@pytest.mark.parametrize(
    "build_response, provider_type, build_success, feedback, expected_feedback, expected_valid, expected_invalid",
    [
        ("etro.gg", "etro.gg", True, "", [], True, False),  # Success case for etro
        (
            "etro.gg",
            "etro.gg",
            False,
            "Error message",
            "Error message",
            False,
            True,
        ),  # Error case for etro
        (
            "xivgear.app",
            "xivgear.app",
            True,
            "",
            [],
            True,
            False,
        ),  # Success case for xivgear
        (
            "xivgear.app",
            "xivgear.app",
            False,
            "Error message",
            "Error message",
            False,
            True,
        ),  # Error case for xivgear
    ],
    indirect=["build_response"],
)
def test_process_job_build_url_errors(
    build_response,
    provider_type,
    build_success,
    feedback,
    expected_feedback,
    expected_valid,
    expected_invalid,
    monkeypatch,
):
    """Test process_job_build_url with different error cases for both providers."""
    url = (
        "https://etro.gg/gearset/123456"
        if provider_type == "etro.gg"
        else "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501"
    )
    selected_role = "Melee"

    # Modify our fixture for this test case to include the success/failure states
    modified_response = list(build_response)
    modified_response[0] = build_success
    modified_response[1] = feedback

    # Mock the appropriate build function to return our modified fixture
    monkeypatch.setattr("crit_app.pages.analysis.etro_build", lambda x: tuple(modified_response))
    monkeypatch.setattr("crit_app.pages.analysis.xiv_gear_build", lambda x: tuple(modified_response))

    # Call the function
    result = process_job_build_url(1, url, selected_role)

    # Check that the feedback and validation states match what we expect
    assert result[0] == expected_feedback
    assert result[2] is expected_valid
    assert result[3] is expected_invalid
