from unittest.mock import MagicMock, patch

import dash
import pytest
from dash import html
from dash.exceptions import PreventUpdate

from crit_app.job_data.encounter_data import (
    stat_ranges,
)
from crit_app.job_data.roles import role_stat_dict

# Mock dash.register_page at the module level, before importing
# This prevents the PageError during import
with patch("dash.register_page"):
    # Now it's safe to import the modules
    from crit_app.pages.analysis import (
        analyze_and_register_rotation,
        display_bottom_build_row,
        display_compute_button,
        fill_job_build_via_xiv_gear_select,
        fill_role_stat_labels,
        fill_xiv_gear_build_selector,
        metas,
        page_title,
        valid_critical_hit,
        valid_determination,
        valid_direct_hit,
        valid_main_stat,
        valid_speed,
        valid_tenacity,
        valid_weapon_damage,
    )


# Test parameters for validation functions
VALID_STAT = (True, False)
INVALID_STAT = (False, True)


@pytest.mark.parametrize(
    "tenacity, role, expected",
    [
        (100, "Tank", INVALID_STAT),  # Too low for Tank
        (400, "Tank", VALID_STAT),  # Valid for Tank
        (5000, "Tank", INVALID_STAT),  # Too high for Tank
        (None, "Tank", INVALID_STAT),  # None value should be invalid
        (400, "Healer", VALID_STAT),  # Always valid for non-Tank
        (100, "Healer", VALID_STAT),  # Always valid for non-Tank
        (5000, "Healer", VALID_STAT),  # Always valid for non-Tank
        (None, "Healer", VALID_STAT),  # None value should be valid for non-Tank
    ],
)
def test_valid_tenacity(tenacity, role, expected):
    """Test the tenacity validation function with various inputs."""
    result = valid_tenacity(tenacity, role)
    assert result == expected


@pytest.mark.parametrize(
    "main_stat, expected",
    [
        (stat_ranges["main_stat"]["lower"] + 10, VALID_STAT),  # Valid main stat
        (stat_ranges["main_stat"]["lower"] - 10, INVALID_STAT),  # Too low
        (stat_ranges["main_stat"]["upper"] + 10, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_main_stat(main_stat, expected):
    """Test the main stat validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_main_stat(main_stat)
    else:
        result = valid_main_stat(main_stat)
        assert result == expected


@pytest.mark.parametrize(
    "determination, expected",
    [
        (stat_ranges["DET"]["lower"] + 10, VALID_STAT),  # Valid determination
        (stat_ranges["DET"]["lower"] - 10, INVALID_STAT),  # Too low
        (stat_ranges["DET"]["upper"] + 10, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_determination(determination, expected):
    """Test the determination validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_determination(determination)
    else:
        result = valid_determination(determination)
        assert result == expected


@pytest.mark.parametrize(
    "speed, expected",
    [
        (stat_ranges["SPEED"]["lower"] + 10, VALID_STAT),  # Valid speed
        (stat_ranges["SPEED"]["lower"] - 10, INVALID_STAT),  # Too low
        (stat_ranges["SPEED"]["upper"] + 10, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_speed(speed, expected):
    """Test the speed validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_speed(speed)
    else:
        result = valid_speed(speed)
        assert result == expected


@pytest.mark.parametrize(
    "critical_hit, expected",
    [
        (stat_ranges["CRT"]["lower"] + 10, VALID_STAT),  # Valid critical hit
        (stat_ranges["CRT"]["lower"] - 10, INVALID_STAT),  # Too low
        (stat_ranges["CRT"]["upper"] + 10, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_critical_hit(critical_hit, expected):
    """Test the critical hit validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_critical_hit(critical_hit)
    else:
        result = valid_critical_hit(critical_hit)
        assert result == expected


@pytest.mark.parametrize(
    "direct_hit, expected",
    [
        (stat_ranges["DH"]["lower"] + 10, VALID_STAT),  # Valid direct hit
        (stat_ranges["DH"]["lower"] - 10, INVALID_STAT),  # Too low
        (stat_ranges["DH"]["upper"] + 10, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_direct_hit(direct_hit, expected):
    """Test the direct hit validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_direct_hit(direct_hit)
    else:
        result = valid_direct_hit(direct_hit)
        assert result == expected


@pytest.mark.parametrize(
    "weapon_damage, expected",
    [
        (379, VALID_STAT),  # Valid weapon damage
        (400, INVALID_STAT),  # Too high
        (None, "invalid"),  # None should raise PreventUpdate
    ],
)
def test_valid_weapon_damage(weapon_damage, expected):
    """Test the weapon damage validation function with various inputs."""
    if expected == "invalid":
        with pytest.raises(PreventUpdate):
            valid_weapon_damage(weapon_damage)
    else:
        result = valid_weapon_damage(weapon_damage)
        assert result == expected


@pytest.mark.parametrize(
    "analysis_id, expected_title",
    [
        (None, ""),  # No analysis ID should return empty title
        ("nonexistent_id", ""),  # Invalid analysis ID should return empty title
    ],
)
def test_page_title_invalid_id(analysis_id, expected_title, monkeypatch):
    """Test page_title function when analysis ID is invalid or missing."""
    # Mock check_valid_player_analysis_id to return False
    with patch("crit_app.pages.analysis.check_valid_player_analysis_id", return_value=False):
        assert page_title(analysis_id) == expected_title


@pytest.mark.parametrize(
    "analysis_id, player_info, expected_title",
    [
        (
            "valid_id",
            ("Player1", "WAR", "E12S", 360),
            "Analysis: Player1 (WAR); E12S (6:00)",
        ),
        (
            "valid_id",
            ("Player2", "WHM", "P4S", 480),
            "Analysis: Player2 (WHM); P4S (8:00)",
        ),
    ],
)
def test_page_title_valid_id(analysis_id, player_info, expected_title):
    """Test page_title function with a valid analysis ID."""
    # Mock the required functions to return test data
    with (
        patch("crit_app.pages.analysis.check_valid_player_analysis_id", return_value=True),
        patch("crit_app.pages.analysis.player_analysis_meta_info", return_value=player_info),
        patch("crit_app.pages.analysis.abbreviated_job_map", {"WAR": "war", "WHM": "whm"}),
        patch(
            "crit_app.pages.analysis.format_kill_time_str",
            side_effect=lambda t: f"{t//60}:{t%60:02d}",
        ),
    ):
        assert page_title(analysis_id) == expected_title


@pytest.mark.parametrize(
    "analysis_id, valid_id, player_info",
    [
        (None, False, ("Player1", "WAR", "E12S", 360)),
        ("invalid_id", False, ("Player1", "WAR", "E12S", 360)),
        ("valid_id", True, ("Player1", "WAR", "E12S", 360)),
    ],
)
def test_metas_function(analysis_id, valid_id, player_info):
    """Test the metas function generates the correct meta tags."""
    with (
        patch("crit_app.pages.analysis.check_valid_player_analysis_id", return_value=valid_id),
        patch("crit_app.pages.analysis.player_analysis_meta_info", return_value=player_info),
        patch("crit_app.pages.analysis.abbreviated_job_map", {"WAR": "war"}),
        patch("crit_app.pages.analysis.format_kill_time_str", return_value="6:00"),
    ):
        result = metas(analysis_id)

        # Basic validation of meta tags
        assert isinstance(result, list)
        assert all(isinstance(tag, dict) for tag in result)

        # Check specific meta tags
        viewport_tag = next((tag for tag in result if tag.get("name") == "viewport"), None)
        assert viewport_tag is not None
        assert viewport_tag["content"] == "width=device-width, initial-scale=1"

        # Check twitter and og tags exist
        twitter_tags = [tag for tag in result if tag.get("property", "").startswith("twitter:")]
        og_tags = [tag for tag in result if tag.get("property", "").startswith("og:")]
        assert len(twitter_tags) > 0
        assert len(og_tags) > 0


@pytest.mark.parametrize(
    "gear_data, expected_options, expected_value",
    [
        (
            {
                "data": [
                    ("PLD", "Tank Build 1", "Tank", 3000, 1000, 2500, 2000, 400, 120, 1200),
                    ("WAR", "Tank Build 2", "Tank", 3100, 950, 2600, 1900, 450, 125, 1250),
                ],
                "gear_index": 0,
            },
            [
                {"label": "Tank Build 1", "value": "0"},
                {"label": "Tank Build 2", "value": "1"},
            ],
            "0",
        ),
        (
            {
                "data": [
                    ("DRG", "Melee Build 1", "Melee", 3100, 1200, 2700, 2200, 600, 140, 400),
                    ("NIN", "Melee Build 2", "Melee", 3050, 1250, 2650, 2250, 650, 145, 400),
                    ("MNK", "Melee Build 3", "Melee", 3200, 1100, 2800, 2150, 550, 142, 400),
                ],
                "gear_index": 1,
            },
            [
                {"label": "Melee Build 1", "value": "0"},
                {"label": "Melee Build 2", "value": "1"},
                {"label": "Melee Build 3", "value": "2"},
            ],
            "1",
        ),
        (
            {
                "data": [
                    ("BLM", "Caster Build 1", "Magical Ranged", 3400, 1400, 2900, 2400, 800, 160, 400),
                    ("SMN", "Caster Build 2", "Magical Ranged", 3450, 1350, 2950, 2350, 750, 158, 400),
                ],
                "gear_index": -1,
            },
            [
                {"label": "Caster Build 1", "value": "0"},
                {"label": "Caster Build 2", "value": "1"},
            ],
            None,
        ),
        (
            None,  # Should raise PreventUpdate
            [],
            None,
        ),
        (
            {},  # Empty dict should raise PreventUpdate
            [],
            None,
        ),
    ],
)
def test_fill_xiv_gear_build_selector(gear_data, expected_options, expected_value):
    """Test that the xiv gear build selector is correctly populated based on the input data."""

    # For None or empty dict cases, we expect PreventUpdate
    if gear_data is None or gear_data == {}:
        with pytest.raises(PreventUpdate):
            fill_xiv_gear_build_selector(gear_data)
    else:
        # Call the function and check that it returns expected values
        options, value = fill_xiv_gear_build_selector(gear_data)
        assert options == expected_options
        assert value == expected_value


@pytest.mark.parametrize(
    "gear_sheet_data, index, expected",
    [
        (
            {
                "data": [
                    ["PLD", "Tank Build 1", "Tank", 3000, 1000, 2500, 2000, 400, 120, 1200],
                    ["WAR", "Tank Build 2", "Tank", 3100, 950, 2600, 1900, 450, 125, 1250],
                ]
            },
            "0",
            (html.H4("Build name: Tank Build 1"), 3000, 1000, 2500, 2000, 400, 120, 1200),
        ),
        (
            {
                "data": [
                    ["WHM", "Healer Build 1", "Healer", 3200, 1100, 2600, 2100, 500, 130, 400],
                    ["SCH", "Healer Build 2", "Healer", 3150, 1150, 2550, 2150, 480, 128, 400],
                ]
            },
            "1",
            (html.H4("Build name: Healer Build 2"), 3150, 1150, 2550, 2150, 480, 128, 400),
        ),
        (
            {
                "data": [
                    ["BRD", "Ranged Build 1", "Physical Ranged", 3300, 1300, 2800, 2300, 700, 150, 400],
                    ["MCH", "Ranged Build 2", "Physical Ranged", 3250, 1350, 2750, 2350, 680, 148, 400],
                    ["DNC", "Ranged Build 3", "Physical Ranged", 3280, 1320, 2820, 2320, 710, 152, 400],
                ]
            },
            "0",
            (html.H4("Build name: Ranged Build 1"), 3300, 1300, 2800, 2300, 700, 150, 400),
        ),
        (
            {
                "data": [
                    ["BLM", "Caster Build 1", "Magical Ranged", 3400, 1400, 2900, 2400, 800, 160, 400],
                    ["SMN", "Caster Build 2", "Magical Ranged", 3450, 1350, 2950, 2350, 750, 158, 400],
                ]
            },
            None,  # Should raise PreventUpdate
            None,
        ),
        (
            {
                "data": [
                    ["DRG", "Melee Build 1", "Melee", 3100, 1200, 2700, 2200, 600, 140, 400],
                    ["MNK", "Melee Build 2", "Melee", 3200, 1100, 2800, 2150, 550, 142, 400],
                ]
            },
            "-1",  # Should raise PreventUpdate
            None,
        ),
    ],
)
def test_fill_job_build_via_xiv_gear_select(gear_sheet_data, index, expected):
    """Test that the job build fields are correctly filled based on the selected gear index."""

    # For None or -1 cases, we expect PreventUpdate
    if index is None or index == "-1":
        with pytest.raises(PreventUpdate):
            fill_job_build_via_xiv_gear_select(gear_sheet_data, index)
    else:
        # Call the function and check that it returns expected values
        result = fill_job_build_via_xiv_gear_select(gear_sheet_data, index)
        assert result[0].children == expected[0].children, "Build names do not match."
        assert result[1:] == expected[1:], "Selected stats do not match."


@pytest.mark.parametrize(
    "role, expected",
    [("Tank", False)]  # Show for Tank
    + [(role, True) for role in list(role_stat_dict.keys()) if role != "Tank"]  # Hide for other roles
    + [("Unsupported", True)],  # Hide for Unsupported
)
def test_display_bottom_build_row(role, expected):
    """Test the display_bottom_build_row function with different roles."""
    result = display_bottom_build_row(role)
    assert result == expected, f"Expected {expected} for role {role}, but got {result}"


@pytest.mark.parametrize(
    "role, expected_outputs",
    # Generate test cases for each role in role_stat_dict
    [
        (
            role,
            (
                role_stat_dict[role]["main_stat"]["label"],
                role_stat_dict[role]["main_stat"]["placeholder"],
                role_stat_dict[role]["speed_stat"]["label"],
                role_stat_dict[role]["speed_stat"]["placeholder"],
            ),
        )
        for role in role_stat_dict.keys()
    ]
    +
    # Add the Unsupported role case
    [("Unsupported", "PreventUpdate")],
)
def test_fill_role_stat_labels(role, expected_outputs):
    """Test the fill_role_stat_labels function with different roles."""
    if expected_outputs == "PreventUpdate":
        # For "Unsupported" role, check that PreventUpdate is raised
        with pytest.raises(PreventUpdate):
            fill_role_stat_labels(role)
    else:
        # For all other roles, check the output values
        main_stat_label, main_stat_placeholder, speed_tooltip, speed_stat_placeholder = fill_role_stat_labels(role)

        # The labels for "Healer" and "Magical Ranged" are special cases with HTML elements
        if role in ["Healer", "Magical Ranged"] and isinstance(expected_outputs[0], list):
            # For roles with HTML elements, check the first HTML element's children
            if isinstance(main_stat_label, list):
                assert (
                    main_stat_label[0].children == expected_outputs[0][0].children
                ), f"Main stat label mismatch for {role}"
            else:
                # Direct comparison for string to string
                assert main_stat_label == expected_outputs[0], f"Main stat label mismatch for {role}"
        else:
            # Direct comparison for roles with simple string labels
            assert main_stat_label == expected_outputs[0], f"Main stat label mismatch for {role}"

        assert main_stat_placeholder == expected_outputs[1], f"Main stat placeholder mismatch for {role}"
        assert speed_tooltip == expected_outputs[2], f"Speed tooltip mismatch for {role}"
        assert speed_stat_placeholder == expected_outputs[3], f"Speed stat placeholder mismatch for {role}"


@pytest.mark.parametrize(
    "healers, tanks, melees, phys_ranged, magic_ranged, healer_value, tank_value, melee_value, phys_ranged_value, magic_ranged_value, expected",
    [
        # Case 1: No data loaded at all (empty lists, all values None)
        ([], [], [], [], [], None, None, None, None, None, True),
        # Case 2: Job lists with data but no selection
        (
            [{"value": 1, "label": "WHM"}],
            [{"value": 2, "label": "WAR"}],
            [{"value": 3, "label": "MNK"}],
            [{"value": 4, "label": "BRD"}],
            [{"value": 5, "label": "BLM"}],
            None,
            None,
            None,
            None,
            None,
            True,
        ),
        # Case 3: Valid selection - healer selected
        (
            [{"value": 1, "label": "WHM"}],
            [{"value": 2, "label": "WAR"}],
            [{"value": 3, "label": "MNK"}],
            [{"value": 4, "label": "BRD"}],
            [{"value": 5, "label": "BLM"}],
            1,
            None,
            None,
            None,
            None,
            False,
        ),
        # Case 4: Valid selection - tank selected
        (
            [{"value": 1, "label": "WHM"}],
            [{"value": 2, "label": "WAR"}],
            [{"value": 3, "label": "MNK"}],
            [{"value": 4, "label": "BRD"}],
            [{"value": 5, "label": "BLM"}],
            None,
            2,
            None,
            None,
            None,
            False,
        ),
        # Case 5: Invalid selection (selected job not in list)
        (
            [{"value": 1, "label": "WHM"}],
            [{"value": 2, "label": "WAR"}],
            [{"value": 3, "label": "MNK"}],
            [{"value": 4, "label": "BRD"}],
            [{"value": 5, "label": "BLM"}],
            999,
            None,
            None,
            None,
            None,
            True,
        ),
        # Case 6: Multiple selections (should use only first non-None value)
        (
            [{"value": 1, "label": "WHM"}],
            [{"value": 2, "label": "WAR"}],
            [{"value": 3, "label": "MNK"}],
            [{"value": 4, "label": "BRD"}],
            [{"value": 5, "label": "BLM"}],
            1,
            2,
            3,
            None,
            None,
            False,  # 1 is selected first and is valid
        ),
        # Case 7: Job lists with disabled jobs
        (
            [{"value": 1, "label": "WHM", "disabled": True}],
            [{"value": 2, "label": "WAR", "disabled": False}],
            [],
            [],
            [],
            1,
            None,
            None,
            None,
            None,
            True,  # Even though job 1 is selected, it's disabled so should be hidden
        ),
        # Case 8: None job_list (edge case handling)
        (None, None, None, None, None, 1, None, None, None, None, True),
        # Case 9: Empty job_list but with a selection (should still hide)
        ([], [], [], [], [], 1, None, None, None, None, True),
    ],
)
def test_display_compute_button(
    healers,
    tanks,
    melees,
    phys_ranged,
    magic_ranged,
    healer_value,
    tank_value,
    melee_value,
    phys_ranged_value,
    magic_ranged_value,
    expected,
):
    """Test the display_compute_button function with various inputs.

    This tests whether the compute button is correctly shown/hidden based on job selections.

    Args:
        healers: List of healer job options
        tanks: List of tank job options
        melees: List of melee job options
        phys_ranged: List of physical ranged job options
        magic_ranged: List of magical ranged job options
        healer_value: Selected healer job ID
        tank_value: Selected tank job ID
        melee_value: Selected melee job ID
        phys_ranged_value: Selected physical ranged job ID
        magic_ranged_value: Selected magical ranged job ID
        expected: Whether the compute button should be hidden (True) or shown (False)
    """
    # Handle None values for job lists
    healers = [] if healers is None else healers
    tanks = [] if tanks is None else tanks
    melees = [] if melees is None else melees
    phys_ranged = [] if phys_ranged is None else phys_ranged
    magic_ranged = [] if magic_ranged is None else magic_ranged

    result = display_compute_button(
        healers,
        tanks,
        melees,
        phys_ranged,
        magic_ranged,
        healer_value,
        tank_value,
        melee_value,
        phys_ranged_value,
        magic_ranged_value,
    )
    assert result == expected, (
        f"Expected {expected} but got {result} for selection: "
        + f"[{healer_value}, {tank_value}, {melee_value}, {phys_ranged_value}, {magic_ranged_value}]"
    )


@pytest.mark.parametrize(
    "player_ids, fflogs_data, mock_setup, expected_error_text",
    [
        # Case 1: No player selected
        (
            [None, None, None, None, None],
            {"report_id": "abc123", "fight_id": 1},
            {},  # No mocks needed
            "No player selected",
        ),
        # Case 2: FFLogs error message test
        (
            [None, "12345", None, None, None],  # Tank selected
            None,  # Force using parse_fflogs_url
            {
                "parse_fflogs_url": ("abc123", "last", ""),
                "_query_last_fight_id": (0, "Error: Could not find last fight"),
            },
            "Error: Could not find last fight",
        ),
        # Case 3: Player name is None
        (
            [None, "12345", None, None, None],  # Tank selected
            {"report_id": "abc123", "fight_id": 1},
            {"read_player_analysis_info": (None, None, None, None, None, None, None, None)},
            "Please resubmit Log URL",
        ),
    ],
)
def test_analyze_and_register_rotation_early_returns(player_ids, fflogs_data, mock_setup, expected_error_text):
    """Test analyze_and_register_rotation when different early return conditions are met."""
    # Extract player IDs
    healer_value, tank_value, melee_value, phys_ranged_value, magic_ranged_value = player_ids

    # Set up any required mocks
    with patch.multiple(
        "crit_app.pages.analysis",
        parse_fflogs_url=MagicMock(return_value=mock_setup.get("parse_fflogs_url", (None, None, ""))),
        _query_last_fight_id=MagicMock(return_value=mock_setup.get("_query_last_fight_id", (0, ""))),
        read_player_analysis_info=MagicMock(
            return_value=mock_setup.get("read_player_analysis_info", (None, None, None, None, None, None, None, None))
        ),
    ):
        # Mock inputs
        n_clicks = 1
        main_stat_pre_bonus = 3000
        tenacity = 400
        determination = 2500
        speed_stat = 2000
        ch = 2200
        dh = 1200
        wd = 120
        job_build_idx = None
        medication_amt = 1000
        fflogs_url = "https://www.fflogs.com/reports/abc123#fight=1"
        fight_phase = 1
        job_build_url = "https://etro.gg/gearset/123456"

        # Call the function
        result = analyze_and_register_rotation(
            n_clicks,
            main_stat_pre_bonus,
            tenacity,
            determination,
            speed_stat,
            ch,
            dh,
            wd,
            job_build_idx,
            medication_amt,
            fflogs_data,
            fflogs_url,
            fight_phase,
            job_build_url,
            healer_value,
            tank_value,
            melee_value,
            phys_ranged_value,
            magic_ranged_value,
        )

        # Check the returned values
        assert result[0] == dash.no_update  # url should be no_update
        assert result[1] == ["Analyze rotation"]  # button text returns to normal
        assert result[2] is False  # button should not be disabled
        assert expected_error_text in str(result[3][0])  # error message contains the expected text
        assert result[4] is False  # results div should not be hidden
