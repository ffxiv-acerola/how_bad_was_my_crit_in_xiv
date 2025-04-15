from unittest.mock import MagicMock, patch

import pytest
from dash.exceptions import PreventUpdate

# Mock both dash.register_page and dash.get_app at the module level
# This prevents the PageError and app not defined errors during import
with patch("dash.register_page"), patch("dash.get_app", return_value=MagicMock()):
    # Now it's safe to import the modules
    from crit_app.pages.party_analysis import job_build_process

# build_response fixture is now imported from conftest.py


def test_job_build_process_none_clicks():
    """Test that job_build_process raises PreventUpdate when n_clicks is None."""
    with pytest.raises(PreventUpdate):
        job_build_process(None, "https://etro.gg/gearset/123456", "STR/DEX:", 3000, 0, 1800, 400, 2500, 1400, 130)


@pytest.mark.parametrize(
    "url, provider, main_stat_label",
    [
        ("https://etro.gg/gearset/123456", "etro.gg", "STR/DEX:"),
        (
            "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501",
            "xivgear.app",
            "STR:",
        ),
        ("https://invalid-url.com/gearset/123456", "invalid", "MND:"),
    ],
)
def test_job_build_process_provider_detection(url, provider, main_stat_label, monkeypatch):
    """Test that job_build_process correctly identifies the provider."""
    # Mock job_build_provider to return our expected values
    if provider == "invalid":
        monkeypatch.setattr(
            "crit_app.pages.party_analysis.job_build_provider",
            lambda x: (False, "Only etro.gg or xivgear.app is supported."),
        )
        # For invalid URLs, we should get the error message in the feedback
        result = job_build_process(1, url, main_stat_label, 3000, 0, 1800, 400, 2500, 1400, 130)
        assert result[0] == "Only etro.gg or xivgear.app is supported."
    else:
        monkeypatch.setattr("crit_app.pages.party_analysis.job_build_provider", lambda x: (True, provider))
        # For this test, we don't care about the actual build calls, just that the right one is chosen
        monkeypatch.setattr(
            "crit_app.pages.party_analysis.etro_build",
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
            "crit_app.pages.party_analysis.xiv_gear_build",
            lambda x, require_sheet_selection=False: (
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

        result = job_build_process(1, url, main_stat_label, 3000, 0, 1800, 400, 2500, 1400, 130)
        assert result[0] == "Mocked error"


# List of test parameters for each provider
provider_params = [
    # (provider type, url, main_stat_label, expected_role)
    ("etro.gg", "etro.gg", "https://etro.gg/gearset/123456", "STR/DEX:", "Melee"),
    (
        "xivgear.app",
        "xivgear.app",
        "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501",
        "STR/DEX:",
        "Melee",
    ),
]


@pytest.mark.parametrize(
    "build_response, provider_type, url, main_stat_label, expected_role",
    provider_params,
    indirect=["build_response"],
)
def test_job_build_process_with_provider(
    build_response, provider_type, url, main_stat_label, expected_role, monkeypatch
):
    """Test job_build_process with different providers using parameterization."""
    # Mock job_build_provider to return the appropriate provider
    monkeypatch.setattr(
        "crit_app.pages.party_analysis.job_build_provider",
        lambda x: (True, provider_type),
    )

    # Mock time.sleep to avoid delay
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Mock the build functions
    if provider_type == "etro.gg":
        monkeypatch.setattr("crit_app.pages.party_analysis.etro_build", lambda x: build_response)
    else:
        monkeypatch.setattr(
            "crit_app.pages.party_analysis.xiv_gear_build", lambda x, require_sheet_selection=True: build_response
        )

    # Call the function
    result = job_build_process(1, url, main_stat_label, 3000, 0, 1800, 400, 2500, 1400, 130)

    # Check basic response structure
    assert result[0] == []  # No feedback for successful call
    assert result[1] is True  # job_build_valid
    assert result[2] is False  # job_build_invalid
    assert result[3] == f"Build name: {build_response[5][0].children}"  # build_name

    # Check that stats are correctly loaded
    assert result[4] == build_response[7]  # Main stat
    assert result[5] == build_response[8]  # DET
    assert result[6] == build_response[9]  # Speed stat
    assert result[7] == build_response[10]  # CRT
    assert result[8] == build_response[11]  # DH
    assert result[9] == build_response[12]  # WD
    assert result[10] == build_response[13]  # TEN


@pytest.mark.parametrize(
    "build_response, provider_type, selected_role, main_stat_label, expected_feedback",
    [
        ("etro.gg", "etro.gg", "Melee", "STR/DEX:", []),  # Matching role - should succeed
        ("etro.gg", "etro.gg", "Tank", "STR:", "A non-Tank etro build was used."),  # Mismatched role
        ("xivgear.app", "xivgear.app", "Melee", "STR/DEX:", []),  # Matching role - should succeed
        ("xivgear.app", "xivgear.app", "Healer", "MND:", "A non-Healer etro build was used."),  # Mismatched role
    ],
    indirect=["build_response"],
)
def test_job_build_process_role_matching(
    build_response, provider_type, selected_role, main_stat_label, expected_feedback, monkeypatch
):
    """Test job_build_process role matching validation."""
    url = (
        "https://etro.gg/gearset/123456"
        if provider_type == "etro.gg"
        else "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501"
    )

    # Mock job_build_provider and time.sleep
    monkeypatch.setattr(
        "crit_app.pages.party_analysis.job_build_provider",
        lambda x: (True, provider_type),
    )
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Mock the build functions
    if provider_type == "etro.gg":
        monkeypatch.setattr("crit_app.pages.party_analysis.etro_build", lambda x: build_response)
    else:
        monkeypatch.setattr(
            "crit_app.pages.party_analysis.xiv_gear_build", lambda x, require_sheet_selection=True: build_response
        )

    # Call the function
    result = job_build_process(1, url, main_stat_label, 3000, 0, 1800, 400, 2500, 1400, 130)

    # Check if feedback matches expected
    assert result[0] == expected_feedback

    # If roles don't match, check that the function returns invalid_return
    if expected_feedback:
        assert result[1] is False  # Valid should be False for mismatched roles
        assert result[2] is True  # Invalid should be True for mismatched roles


@pytest.mark.parametrize(
    "build_response, provider_type, build_success, feedback, expected_valid, expected_invalid",
    [
        ("etro.gg", "etro.gg", True, [], True, False),  # Success case for etro
        ("etro.gg", "etro.gg", False, "Error message", False, True),  # Error case for etro
        ("xivgear.app", "xivgear.app", True, [], True, False),  # Success case for xivgear
        ("xivgear.app", "xivgear.app", False, "Error message", False, True),  # Error case for xivgear
    ],
    indirect=["build_response"],
)
def test_job_build_process_error_handling(
    build_response, provider_type, build_success, feedback, expected_valid, expected_invalid, monkeypatch
):
    """Test job_build_process error handling."""
    url = (
        "https://etro.gg/gearset/123456"
        if provider_type == "etro.gg"
        else "https://xivgear.app/?page=sl|f9b260a9-650c-445a-b3eb-c56d8d968501"
    )
    main_stat_label = "STR/DEX:"  # Match the role in the build response

    # Modify our fixture to include the success/failure states
    modified_response = list(build_response)
    modified_response[0] = build_success  # Set job_build_call_successful
    modified_response[1] = feedback  # Set feedback

    # Mock job_build_provider and time.sleep
    monkeypatch.setattr(
        "crit_app.pages.party_analysis.job_build_provider",
        lambda x: (True, provider_type),
    )
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Mock the build functions to return our modified response
    if provider_type == "etro.gg":
        monkeypatch.setattr("crit_app.pages.party_analysis.etro_build", lambda x: tuple(modified_response))
    else:
        monkeypatch.setattr(
            "crit_app.pages.party_analysis.xiv_gear_build",
            lambda x, require_sheet_selection=True: tuple(modified_response),
        )

    # Call the function
    result = job_build_process(1, url, main_stat_label, 3000, 0, 1800, 400, 2500, 1400, 130)

    # Verify error handling
    assert result[0] == feedback
    assert result[1] == expected_valid
    assert result[2] == expected_invalid
