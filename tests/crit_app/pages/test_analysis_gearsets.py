from unittest.mock import patch

import pytest
from dash import html
from dash.exceptions import PreventUpdate

# Mock dash.register_page at the module level, before importing
# This prevents the PageError during import
with patch("dash.register_page"):
    from crit_app.pages.analysis import (
        delete_gearset,
        load_default_gearset,
        load_selected_gearset,
        save_new_gearset,
        set_default_gearset,
        update_gearset,
        validate_save_new_gearset,  # Import renamed function
    )

from crit_app.util.gearset_manager import (
    create_gearset_selector_options,
    set_is_selected_fields,
)

# Sample data
SAVED_GEARSETS_EMPTY = []
SAVED_GEARSETS_ONE = [
    {
        "role": "Tank",
        "name": "Default Tank",
        "main_stat": 3000,
        "determination": 2000,
        "speed": 500,
        "crit": 2500,
        "direct_hit": 1500,
        "weapon_damage": 130,
        "tenacity": 600,
        "is_selected": False,
    }
]
SAVED_GEARSETS_MULTI = [
    {
        "role": "Tank",
        "name": "Default Tank",
        "main_stat": 3000,
        "determination": 2000,
        "speed": 500,
        "crit": 2500,
        "direct_hit": 1500,
        "weapon_damage": 130,
        "tenacity": 600,
        "is_selected": False,
    },
    {
        "role": "Healer",
        "name": "Healer Set",
        "main_stat": 3100,
        "determination": 1900,
        "speed": 700,
        "crit": 2600,
        "direct_hit": 1400,
        "weapon_damage": 128,
        "is_selected": False,
    },
]

# Incomplete gearset for testing (case 4)
INCOMPLETE_GEARSET = [
    {
        "role": "Melee",
        "name": "Partial Set",
        # Missing some stats
        "main_stat": 3400,
        "crit": 2800,
        "is_selected": False,
    }
]

# Gearset with pre-selected item for testing (case 5)
PRE_SELECTED_GEARSETS = [
    {
        "role": "Tank",
        "name": "Tank Set",
        "main_stat": 3000,
        "determination": 2000,
        "speed": 500,
        "crit": 2500,
        "direct_hit": 1500,
        "weapon_damage": 130,
        "tenacity": 600,
        "is_selected": False,  # Not selected
    },
    {
        "role": "Healer",
        "name": "Healer Set",
        "main_stat": 3100,
        "determination": 1900,
        "speed": 700,
        "crit": 2600,
        "direct_hit": 1400,
        "weapon_damage": 128,
        "is_selected": True,  # Pre-selected
    },
]

CURRENT_STATS = {
    "role": "Melee",
    "main_stat": 3200,
    "det": 2100,
    "speed": 600,
    "crit": 2700,
    "dh": 1600,
    "wd": 135,
    "ten": None,
}

NO_DEFAULT_VALUE = "-1"


@pytest.mark.parametrize(
    "analysis_indicator, default_gear_index, saved_gearsets, current_stats, expected_stats, expected_name_div, expected_dropdown_value, expected_selected_index",
    [
        # 1. New Analysis, Valid Default (Multi)
        (
            False,
            0,
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            {
                "role": "Tank",
                "main_stat": 3000,
                "det": 2000,
                "speed": 500,
                "crit": 2500,
                "dh": 1500,
                "wd": 130,
                "ten": 600,
            },
            [html.H4("Build name: Default Tank")],
            "0",
            0,
        ),
        # 2. Existing Analysis, Valid Default (Multi) - Should load current stats
        (
            True,
            0,
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            "0",
            -1,  # No selection for existing analysis
        ),
        # 3. New Analysis, No Default Index (Multi)
        (
            False,
            None,
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            NO_DEFAULT_VALUE,
            -1,
        ),
        # 4. New Analysis, Invalid Default Index (Multi)
        (
            False,
            99,
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            NO_DEFAULT_VALUE,
            -1,
        ),
        # 5. New Analysis, No Gearsets
        (
            False,
            None,
            SAVED_GEARSETS_EMPTY,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            NO_DEFAULT_VALUE,
            -1,
        ),
        # 6. Existing Analysis, No Gearsets
        (
            True,
            None,
            SAVED_GEARSETS_EMPTY,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            NO_DEFAULT_VALUE,
            -1,
        ),
        # 7. New Analysis, Valid Default (Single)
        (
            False,
            0,
            SAVED_GEARSETS_ONE,
            CURRENT_STATS,
            {
                "role": "Tank",
                "main_stat": 3000,
                "det": 2000,
                "speed": 500,
                "crit": 2500,
                "dh": 1500,
                "wd": 130,
                "ten": 600,
            },
            [html.H4("Build name: Default Tank")],
            "0",
            0,
        ),
        # 8. Existing Analysis, Valid Default (Single)
        (
            True,
            0,
            SAVED_GEARSETS_ONE,
            CURRENT_STATS,
            CURRENT_STATS,
            [],
            "0",
            -1,
        ),
        # 9. String Default Index - Should convert to integer
        (
            False,
            "0",  # String index that needs conversion
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            {
                "role": "Tank",
                "main_stat": 3000,
                "det": 2000,
                "speed": 500,
                "crit": 2500,
                "dh": 1500,
                "wd": 130,
                "ten": 600,
            },
            [html.H4("Build name: Default Tank")],
            "0",
            0,
        ),
        # 10. Empty String Default Index - Should treat as None
        (
            False,
            "",  # Empty string should be treated as None
            SAVED_GEARSETS_MULTI,
            CURRENT_STATS,
            CURRENT_STATS,  # No default gear values loaded
            [],
            NO_DEFAULT_VALUE,
            -1,
        ),
        # 11. Incomplete Gearset Data - Should handle missing fields with None/defaults
        (
            False,
            0,
            INCOMPLETE_GEARSET,
            CURRENT_STATS,
            {
                "role": "Melee",
                "main_stat": 3400,
                "det": None,  # Missing in gearset
                "speed": None,  # Missing in gearset
                "crit": 2800,
                "dh": None,  # Missing in gearset
                "wd": None,  # Missing in gearset
                "ten": None,  # Missing in gearset
            },
            [html.H4("Build name: Partial Set")],
            "0",
            0,
        ),
        # 12. Pre-Selected Gearset - Should override pre-selection based on default_gear_index
        (
            False,
            0,  # Select first gearset as default, overriding existing selection
            PRE_SELECTED_GEARSETS,
            CURRENT_STATS,
            {
                "role": "Tank",
                "main_stat": 3000,
                "det": 2000,
                "speed": 500,
                "crit": 2500,
                "dh": 1500,
                "wd": 130,
                "ten": 600,
            },
            [html.H4("Build name: Tank Set")],
            "0",
            0,  # Selection moved to index 0
        ),
    ],
)
def test_load_default_gearset(
    analysis_indicator,
    default_gear_index,
    saved_gearsets,
    current_stats,
    expected_stats,
    expected_name_div,
    expected_dropdown_value,
    expected_selected_index,
):
    """Test the load_default_gearset callback for various scenarios."""
    # Deep copy gearsets to avoid modification across tests if necessary (though primitives should be fine)
    gearsets_input = [gs.copy() for gs in saved_gearsets]

    # Calculate expected selector options based on the input gearsets
    expected_options = create_gearset_selector_options(gearsets_input)

    # Calculate expected gearset data (with correct selection state)
    expected_gearsets_data = set_is_selected_fields(gearsets_input, expected_selected_index)

    # Call the function under test
    (
        actual_role,
        actual_main_stat,
        actual_det,
        actual_speed,
        actual_crit,
        actual_dh,
        actual_wd,
        actual_ten,
        actual_name_div,
        actual_options,
        actual_gearsets_data,
        actual_dropdown_value,
    ) = load_default_gearset(
        analysis_indicator,
        default_gear_index,
        gearsets_input,  # Pass the copied list
        current_stats["role"],
        current_stats["main_stat"],
        current_stats["det"],
        current_stats["speed"],
        current_stats["crit"],
        current_stats["dh"],
        current_stats["wd"],
        current_stats["ten"],
    )

    # Assertions for stats
    assert actual_role == expected_stats["role"]
    assert actual_main_stat == expected_stats["main_stat"]
    assert actual_det == expected_stats["det"]
    assert actual_speed == expected_stats["speed"]
    assert actual_crit == expected_stats["crit"]
    assert actual_dh == expected_stats["dh"]
    assert actual_wd == expected_stats["wd"]
    assert actual_ten == expected_stats["ten"]

    # Assertion for job build name div (handle potential list comparison issues)
    # Convert html components to string for comparison if necessary, or compare structure
    assert str(actual_name_div) == str(expected_name_div)

    # Assertion for selector options
    assert actual_options == expected_options

    # Assertion for updated gearsets data (including selection state)
    assert actual_gearsets_data == expected_gearsets_data

    # Assertion for dropdown value
    assert actual_dropdown_value == expected_dropdown_value


@pytest.mark.parametrize(
    "selected_value, saved_gearsets, expected_output",
    [
        # 1. Select first item in multi-list
        ("0", SAVED_GEARSETS_MULTI, 0),
        # 2. Select second item in multi-list
        ("1", SAVED_GEARSETS_MULTI, 1),
        # 3. Select "No Default" in multi-list
        (NO_DEFAULT_VALUE, SAVED_GEARSETS_MULTI, None),
        # 4. Select invalid index (out of bounds) in multi-list
        ("5", SAVED_GEARSETS_MULTI, None),
        # 5. Select None input in multi-list
        (None, SAVED_GEARSETS_MULTI, None),
        # 6. Select first item in single-list
        ("0", SAVED_GEARSETS_ONE, 0),
        # 7. Select "No Default" in single-list
        (NO_DEFAULT_VALUE, SAVED_GEARSETS_ONE, None),
        # 8. Select invalid index (out of bounds) in single-list
        ("1", SAVED_GEARSETS_ONE, None),
        # 9. Select None input in single-list
        (None, SAVED_GEARSETS_ONE, None),
        # 10. Select "No Default" with empty list
        (NO_DEFAULT_VALUE, SAVED_GEARSETS_EMPTY, None),
        # 11. Select invalid index with empty list
        ("0", SAVED_GEARSETS_EMPTY, None),
        # 12. Select None input with empty list
        (None, SAVED_GEARSETS_EMPTY, None),
        # 13. Select non-integer string (should fail conversion and return None)
        ("abc", SAVED_GEARSETS_MULTI, None),
    ],
)
def test_set_default_gearset(selected_value, saved_gearsets, expected_output):
    """Test the set_default_gearset callback function."""
    # Deep copy gearsets to avoid modification across tests if necessary
    gearsets_input = [gs.copy() for gs in saved_gearsets]

    # Call the function under test
    actual_output = set_default_gearset(selected_value, gearsets_input)

    # Assertion
    assert actual_output == expected_output


# Sample data for new gearset
NEW_GEARSET_TANK = {
    "role": "Tank",
    "name": "New Tank Set",
    "main_stat": 3500,
    "determination": 2200,
    "speed": 450,
    "crit": 2400,
    "direct_hit": 1700,
    "weapon_damage": 138,
    "tenacity": 700,
}
NEW_GEARSET_HEALER = {
    "role": "Healer",
    "name": "New Healer Set",
    "main_stat": 3600,
    "determination": 2100,
    "speed": 800,
    "crit": 2700,
    "direct_hit": 1300,
    "weapon_damage": 135,
    "tenacity": None,  # Healers don't use tenacity input field
}


@pytest.mark.parametrize(
    "n_clicks, role, gearset_name, main_stat, tenacity, determination, speed, crit, direct_hit, weapon_damage, initial_saved_gearsets, expected_saved_gearsets, expected_selector_options",
    [
        # 1. Save Tank set to empty list
        (
            1,
            NEW_GEARSET_TANK["role"],
            NEW_GEARSET_TANK["name"],
            NEW_GEARSET_TANK["main_stat"],
            NEW_GEARSET_TANK["tenacity"],
            NEW_GEARSET_TANK["determination"],
            NEW_GEARSET_TANK["speed"],
            NEW_GEARSET_TANK["crit"],
            NEW_GEARSET_TANK["direct_hit"],
            NEW_GEARSET_TANK["weapon_damage"],
            [],
            [
                {
                    "role": "Tank",
                    "name": "New Tank Set",
                    "main_stat": 3500,
                    "determination": 2200,
                    "speed": 450,
                    "crit": 2400,
                    "direct_hit": 1700,
                    "weapon_damage": 138,
                    "tenacity": 700,
                    "is_selected": True,
                }
            ],
            [
                {"label": "No Default", "value": "-1"},
                {"label": "New Tank Set (Tank)", "value": "0"},  # Added (Tank)
            ],
        ),
        # 2. Save Healer set to list with one item
        (
            1,
            NEW_GEARSET_HEALER["role"],
            NEW_GEARSET_HEALER["name"],
            NEW_GEARSET_HEALER["main_stat"],
            NEW_GEARSET_HEALER["tenacity"],  # Should be ignored for Healer
            NEW_GEARSET_HEALER["determination"],
            NEW_GEARSET_HEALER["speed"],
            NEW_GEARSET_HEALER["crit"],
            NEW_GEARSET_HEALER["direct_hit"],
            NEW_GEARSET_HEALER["weapon_damage"],
            SAVED_GEARSETS_ONE,  # Starts with one Tank set
            [
                {  # Existing set, now not selected
                    "role": "Tank",
                    "name": "Default Tank",
                    "main_stat": 3000,
                    "determination": 2000,
                    "speed": 500,
                    "crit": 2500,
                    "direct_hit": 1500,
                    "weapon_damage": 130,
                    "tenacity": 600,
                    "is_selected": False,
                },
                {  # New set, selected
                    "role": "Healer",
                    "name": "New Healer Set",
                    "main_stat": 3600,
                    "determination": 2100,
                    "speed": 800,
                    "crit": 2700,
                    "direct_hit": 1300,
                    "weapon_damage": 135,
                    "is_selected": True,
                    # No tenacity key expected
                },
            ],
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},  # Added (Tank)
                {"label": "New Healer Set (Healer)", "value": "1"},  # Added (Healer)
            ],
        ),
        # 3. Save Tank set to list with multiple items
        (
            1,
            NEW_GEARSET_TANK["role"],
            NEW_GEARSET_TANK["name"],
            NEW_GEARSET_TANK["main_stat"],
            NEW_GEARSET_TANK["tenacity"],
            NEW_GEARSET_TANK["determination"],
            NEW_GEARSET_TANK["speed"],
            NEW_GEARSET_TANK["crit"],
            NEW_GEARSET_TANK["direct_hit"],
            NEW_GEARSET_TANK["weapon_damage"],
            SAVED_GEARSETS_MULTI,  # Starts with Tank and Healer
            [
                {  # Existing Tank, now not selected
                    "role": "Tank",
                    "name": "Default Tank",
                    "main_stat": 3000,
                    "determination": 2000,
                    "speed": 500,
                    "crit": 2500,
                    "direct_hit": 1500,
                    "weapon_damage": 130,
                    "tenacity": 600,
                    "is_selected": False,
                },
                {  # Existing Healer, now not selected
                    "role": "Healer",
                    "name": "Healer Set",
                    "main_stat": 3100,
                    "determination": 1900,
                    "speed": 700,
                    "crit": 2600,
                    "direct_hit": 1400,
                    "weapon_damage": 128,
                    "is_selected": False,
                },
                {  # New Tank, selected
                    "role": "Tank",
                    "name": "New Tank Set",
                    "main_stat": 3500,
                    "determination": 2200,
                    "speed": 450,
                    "crit": 2400,
                    "direct_hit": 1700,
                    "weapon_damage": 138,
                    "tenacity": 700,
                    "is_selected": True,
                },
            ],
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},  # Added (Tank)
                {"label": "Healer Set (Healer)", "value": "1"},  # Added (Healer)
                {"label": "New Tank Set (Tank)", "value": "2"},  # Added (Tank)
            ],
        ),
    ],
)
def test_save_new_gearset(
    n_clicks,
    role,
    gearset_name,
    main_stat,
    tenacity,
    determination,
    speed,
    crit,
    direct_hit,
    weapon_damage,
    initial_saved_gearsets,
    expected_saved_gearsets,
    expected_selector_options,
):
    """Test the save_new_gearset callback function."""
    # Deep copy initial gearsets
    gearsets_input = [gs.copy() for gs in initial_saved_gearsets]

    # Call the function under test
    actual_saved_gearsets, actual_selector_options = save_new_gearset(
        n_clicks,
        role,
        gearset_name,
        main_stat,
        tenacity,
        determination,
        speed,
        crit,
        direct_hit,
        weapon_damage,
        gearsets_input,
    )

    # Assertions
    assert actual_saved_gearsets == expected_saved_gearsets
    assert actual_selector_options == expected_selector_options


@pytest.mark.parametrize(
    "radio_values, radio_ids, saved_gearsets, triggered_info, expected_role, expected_main_stat, expected_det, expected_speed, expected_crit, expected_dh, expected_wd, expected_ten, expected_name_div_str",
    [
        # 1. Select first item (Tank) in multi-list
        (
            [True, False],  # Radio values (first is selected)
            [{"index": 0, "type": "gearset-select"}, {"index": 1, "type": "gearset-select"}],  # Radio IDs
            SAVED_GEARSETS_MULTI,
            {"prop_id": '{"index":0,"type":"gearset-select"}.value', "value": True},  # Trigger info
            "Tank",
            3000,
            2000,
            500,
            2500,
            1500,
            130,
            600,  # Expected stats
            str([html.H4("Build name: Default Tank")]),  # Expected name div (as string)
        ),
        # 2. Select second item (Healer) in multi-list
        (
            [False, True],
            [{"index": 0, "type": "gearset-select"}, {"index": 1, "type": "gearset-select"}],
            SAVED_GEARSETS_MULTI,
            {"prop_id": '{"index":1,"type":"gearset-select"}.value', "value": True},
            "Healer",
            3100,
            1900,
            700,
            2600,
            1400,
            128,
            None,  # Tenacity is None
            str([html.H4("Build name: Healer Set")]),
        ),
        # 3. Select incomplete gearset
        (
            [True],
            [{"index": 0, "type": "gearset-select"}],
            INCOMPLETE_GEARSET,
            {"prop_id": '{"index":0,"type":"gearset-select"}.value', "value": True},
            "Melee",
            3400,
            None,
            None,
            2800,
            None,
            None,
            None,  # Missing stats are None
            str([html.H4("Build name: Partial Set")]),
        ),
        # 4. Select item when list has pre-selected item (should load clicked item)
        (
            [True, False],  # Simulate clicking the first radio, even though second was pre-selected
            [{"index": 0, "type": "gearset-select"}, {"index": 1, "type": "gearset-select"}],
            PRE_SELECTED_GEARSETS,  # Has Healer pre-selected
            {"prop_id": '{"index":0,"type":"gearset-select"}.value', "value": True},  # Trigger for first item (Tank)
            "Tank",
            3000,
            2000,
            500,
            2500,
            1500,
            130,
            600,
            str([html.H4("Build name: Tank Set")]),
        ),
    ],
)
@patch("crit_app.pages.analysis.ctx")  # Mock dash.ctx
def test_load_selected_gearset(
    mock_ctx,
    radio_values,
    radio_ids,
    saved_gearsets,
    triggered_info,
    expected_role,
    expected_main_stat,
    expected_det,
    expected_speed,
    expected_crit,
    expected_dh,
    expected_wd,
    expected_ten,
    expected_name_div_str,
):
    """Test the load_selected_gearset callback function."""
    # Configure the mock_ctx
    mock_ctx.triggered = [triggered_info]

    # Deep copy gearsets
    gearsets_input = [gs.copy() for gs in saved_gearsets]

    # Call the function under test
    (
        actual_role,
        actual_main_stat,
        actual_det,
        actual_speed,
        actual_crit,
        actual_dh,
        actual_wd,
        actual_ten,
        actual_name_div,
    ) = load_selected_gearset(radio_values, radio_ids, gearsets_input)

    # Assertions
    assert actual_role == expected_role
    assert actual_main_stat == expected_main_stat
    assert actual_det == expected_det
    assert actual_speed == expected_speed
    assert actual_crit == expected_crit
    assert actual_dh == expected_dh
    assert actual_wd == expected_wd
    assert actual_ten == expected_ten
    assert str(actual_name_div) == expected_name_div_str


# Sample data for updating gearsets
UPDATE_STATS_TANK = {
    "role": "Tank",
    "main_stat": 3050,
    "tenacity": 650,
    "determination": 2050,
    "speed": 550,
    "crit": 2550,
    "direct_hit": 1550,
    "weapon_damage": 132,
}

UPDATE_STATS_HEALER = {
    "role": "Healer",
    "main_stat": 3150,
    "tenacity": None,  # Should be ignored
    "determination": 1950,
    "speed": 750,
    "crit": 2650,
    "direct_hit": 1450,
    "weapon_damage": 129,
}


@pytest.mark.parametrize(
    "n_clicks_list, triggered_info, initial_saved_gearsets, update_stats, expected_saved_gearsets, expected_selector_options",
    [
        # 1. Update first item (Tank) in multi-list with Tank stats
        (
            [1, None],  # Clicked first update button
            {"type": "gearset-update", "index": 0},
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
            [  # Expected gearsets: first updated and selected, second unchanged and not selected
                {
                    "role": "Tank",
                    "name": "Default Tank",  # Name is preserved
                    "main_stat": 3050,
                    "determination": 2050,
                    "speed": 550,
                    "crit": 2550,
                    "direct_hit": 1550,
                    "weapon_damage": 132,
                    "tenacity": 650,
                    "is_selected": True,  # Updated item is selected
                },
                {
                    "role": "Healer",
                    "name": "Healer Set",
                    "main_stat": 3100,
                    "determination": 1900,
                    "speed": 700,
                    "crit": 2600,
                    "direct_hit": 1400,
                    "weapon_damage": 128,
                    "is_selected": False,  # Other item is not selected
                },
            ],
            [  # Expected options
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},
                {"label": "Healer Set (Healer)", "value": "1"},
            ],
        ),
        # 2. Update second item (Healer) in multi-list with Healer stats
        (
            [None, 1],  # Clicked second update button
            {"type": "gearset-update", "index": 1},
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_HEALER,
            [  # Expected gearsets: first unchanged, second updated and selected
                {
                    "role": "Tank",
                    "name": "Default Tank",
                    "main_stat": 3000,
                    "determination": 2000,
                    "speed": 500,
                    "crit": 2500,
                    "direct_hit": 1500,
                    "weapon_damage": 130,
                    "tenacity": 600,
                    "is_selected": False,
                },
                {
                    "role": "Healer",
                    "name": "Healer Set",  # Name is preserved
                    "main_stat": 3150,
                    "determination": 1950,
                    "speed": 750,
                    "crit": 2650,
                    "direct_hit": 1450,
                    "weapon_damage": 129,
                    # No tenacity expected
                    "is_selected": True,
                },
            ],
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},
                {"label": "Healer Set (Healer)", "value": "1"},
            ],
        ),
        # 3. Update only item (Tank) in single-list with Tank stats
        (
            [1],  # Clicked first (only) update button
            {"type": "gearset-update", "index": 0},
            SAVED_GEARSETS_ONE,
            UPDATE_STATS_TANK,
            [  # Expected gearsets: item updated and selected
                {
                    "role": "Tank",
                    "name": "Default Tank",
                    "main_stat": 3050,
                    "determination": 2050,
                    "speed": 550,
                    "crit": 2550,
                    "direct_hit": 1550,
                    "weapon_damage": 132,
                    "tenacity": 650,
                    "is_selected": True,
                },
            ],
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},
            ],
        ),
        # 6. Update Tank item with Healer stats (should ignore tenacity)
        (
            [1, None],
            {"type": "gearset-update", "index": 0},
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_HEALER,  # Using Healer stats to update a Tank set
            [
                {  # Updated Tank set, now using Healer role/stats, no tenacity
                    "role": "Healer",
                    "name": "Default Tank",  # Name preserved
                    "main_stat": 3150,
                    "determination": 1950,
                    "speed": 750,
                    "crit": 2650,
                    "direct_hit": 1450,
                    "weapon_damage": 129,
                    "is_selected": True,
                },
                {  # Unchanged Healer set
                    "role": "Healer",
                    "name": "Healer Set",
                    "main_stat": 3100,
                    "determination": 1900,
                    "speed": 700,
                    "crit": 2600,
                    "direct_hit": 1400,
                    "weapon_damage": 128,
                    "is_selected": False,
                },
            ],
            [  # Options updated to reflect role change
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Healer)", "value": "0"},  # Role updated in label
                {"label": "Healer Set (Healer)", "value": "1"},
            ],
        ),
    ],
)
@patch("crit_app.pages.analysis.ctx")  # Mock dash.ctx
def test_update_gearset_success(
    mock_ctx,
    n_clicks_list,
    triggered_info,
    initial_saved_gearsets,
    update_stats,
    expected_saved_gearsets,
    expected_selector_options,
):
    """Test the update_gearset callback function for successful updates."""
    # Configure the mock_ctx
    mock_ctx.triggered_id = triggered_info
    # Simulate the structure of ctx.inputs_list for the ALL pattern matching
    mock_ctx.inputs_list = [
        [
            {"id": {"index": i, "type": "gearset-update"}, "property": "n_clicks", "value": n_clicks}
            for i, n_clicks in enumerate(n_clicks_list)
        ]
    ]

    # Deep copy initial gearsets
    gearsets_input = [gs.copy() for gs in initial_saved_gearsets]

    # Call the function under test
    actual_saved_gearsets, actual_selector_options = update_gearset(
        n_clicks_list,
        gearsets_input,
        update_stats["role"],
        update_stats["main_stat"],
        update_stats["tenacity"],
        update_stats["determination"],
        update_stats["speed"],
        update_stats["crit"],
        update_stats["direct_hit"],
        update_stats["weapon_damage"],
    )

    # Assertions
    assert actual_saved_gearsets == expected_saved_gearsets
    assert actual_selector_options == expected_selector_options


@pytest.mark.parametrize(
    "n_clicks_list, triggered_info, initial_saved_gearsets, update_stats",
    [
        # 4. Attempt update with invalid index
        (
            [None, None, 1],  # Clicked hypothetical third button
            {"type": "gearset-update", "index": 2},  # Index 2 is out of bounds for SAVED_GEARSETS_MULTI
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
        # 5. Attempt update with no clicks
        (
            [None, None],  # No clicks
            {"type": "gearset-update", "index": 0},  # Trigger info doesn't matter if no clicks
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
        # 7. Attempt update where triggered_id is not a dict (simulates initial load or non-button trigger)
        (
            [None, None],
            None,  # No triggered_id
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
        # 8. Attempt update where triggered_id is not a dict (invalid trigger)
        (
            [1, None],
            "some-other-id",  # Invalid triggered_id format
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
        # 9. Attempt update where triggered_id type is wrong
        (
            [1, None],
            {"type": "gearset-delete", "index": 0},  # Wrong type
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
        # 10. Attempt update where n_clicks for the triggered button is None or 0
        (
            [None, None],  # n_clicks is None for index 0
            {"type": "gearset-update", "index": 0},
            SAVED_GEARSETS_MULTI,
            UPDATE_STATS_TANK,
        ),
    ],
)
@patch("crit_app.pages.analysis.ctx")  # Mock dash.ctx
def test_update_gearset_prevent_update(
    mock_ctx,
    n_clicks_list,
    triggered_info,
    initial_saved_gearsets,
    update_stats,
):
    """Test the update_gearset callback function for scenarios causing PreventUpdate."""
    # Configure the mock_ctx
    mock_ctx.triggered_id = triggered_info
    # Simulate the structure of ctx.inputs_list for the ALL pattern matching
    mock_ctx.inputs_list = [
        [
            {"id": {"index": i, "type": "gearset-update"}, "property": "n_clicks", "value": n_clicks}
            for i, n_clicks in enumerate(n_clicks_list)
        ]
    ]

    # Deep copy initial gearsets
    gearsets_input = [gs.copy() for gs in initial_saved_gearsets]

    # Expect PreventUpdate exception
    with pytest.raises(PreventUpdate):
        update_gearset(
            n_clicks_list,
            gearsets_input,
            update_stats["role"],
            update_stats["main_stat"],
            update_stats["tenacity"],
            update_stats["determination"],
            update_stats["speed"],
            update_stats["crit"],
            update_stats["direct_hit"],
            update_stats["weapon_damage"],
        )


# Gearsets with specific default indices for delete testing
SAVED_GEARSETS_MULTI_DEFAULT_0 = [
    {**SAVED_GEARSETS_MULTI[0], "is_selected": True},
    {**SAVED_GEARSETS_MULTI[1], "is_selected": False},
]
SAVED_GEARSETS_MULTI_DEFAULT_1 = [
    {**SAVED_GEARSETS_MULTI[0], "is_selected": False},
    {**SAVED_GEARSETS_MULTI[1], "is_selected": True},
]
SAVED_GEARSETS_ONE_DEFAULT_0 = [
    {**SAVED_GEARSETS_ONE[0], "is_selected": True},
]


@pytest.mark.parametrize(
    "n_clicks_list, triggered_info, initial_saved_gearsets, initial_default_index, expected_saved_gearsets, expected_default_index, expected_selector_options, expected_dropdown_value",
    [
        # 1. Delete first item (not default) in multi-list (default=1)
        (
            [1, None],  # Clicked first delete button
            {"type": "gearset-delete", "index": 0},
            SAVED_GEARSETS_MULTI_DEFAULT_1,  # Default is index 1
            1,
            [  # Expected: Only second item remains
                {**SAVED_GEARSETS_MULTI[1], "is_selected": True},
            ],
            0,  # Default index shifts from 1 to 0
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Healer Set (Healer)", "value": "0"},
            ],
            "0",  # Dropdown value reflects new default index
        ),
        # 2. Delete second item (default) in multi-list (default=1)
        (
            [None, 1],  # Clicked second delete button
            {"type": "gearset-delete", "index": 1},
            SAVED_GEARSETS_MULTI_DEFAULT_1,  # Default is index 1
            1,
            [  # Expected: Only first item remains
                {**SAVED_GEARSETS_MULTI[0], "is_selected": False},
            ],
            None,  # Default index becomes None as it was deleted
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},
            ],
            "-1",  # Dropdown value becomes "No Default"
        ),
        # 3. Delete first item (default) in multi-list (default=0)
        (
            [1, None],
            {"type": "gearset-delete", "index": 0},
            SAVED_GEARSETS_MULTI_DEFAULT_0,  # Default is index 0
            0,
            [
                {**SAVED_GEARSETS_MULTI[1], "is_selected": False},
            ],
            None,  # Default index becomes None
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Healer Set (Healer)", "value": "0"},
            ],
            "-1",
        ),
        # 4. Delete second item (not default) in multi-list (default=0)
        (
            [None, 1],
            {"type": "gearset-delete", "index": 1},
            SAVED_GEARSETS_MULTI_DEFAULT_0,  # Default is index 0
            0,
            [
                {**SAVED_GEARSETS_MULTI[0], "is_selected": True},
            ],
            0,  # Default index remains 0
            [
                {"label": "No Default", "value": "-1"},
                {"label": "Default Tank (Tank)", "value": "0"},
            ],
            "0",
        ),
        # 5. Delete only item (default) in single-list
        (
            [1],
            {"type": "gearset-delete", "index": 0},
            SAVED_GEARSETS_ONE_DEFAULT_0,  # Default is index 0
            0,
            [],  # List becomes empty
            None,  # Default becomes None
            [{"label": "No Default", "value": "-1"}],  # Only "No Default" option
            "-1",
        ),
        # 6. Delete only item (not default) in single-list
        (
            [1],
            {"type": "gearset-delete", "index": 0},
            SAVED_GEARSETS_ONE,  # Default is None implicitly
            None,
            [],
            None,
            [{"label": "No Default", "value": "-1"}],
            "-1",
        ),
    ],
)
@patch("crit_app.pages.analysis.ctx")  # Mock dash.ctx
def test_delete_gearset_success(
    mock_ctx,
    n_clicks_list,
    triggered_info,
    initial_saved_gearsets,
    initial_default_index,
    expected_saved_gearsets,
    expected_default_index,
    expected_selector_options,
    expected_dropdown_value,
):
    """Test the delete_gearset callback function for successful deletions."""
    # Configure the mock_ctx
    mock_ctx.triggered_id = triggered_info
    # Simulate the structure of ctx.inputs_list for the ALL pattern matching
    mock_ctx.inputs_list = [
        [
            {"id": {"index": i, "type": "gearset-delete"}, "property": "n_clicks", "value": n_clicks}
            for i, n_clicks in enumerate(n_clicks_list)
        ]
    ]

    # Deep copy initial gearsets
    gearsets_input = [gs.copy() for gs in initial_saved_gearsets]

    # Call the function under test
    (
        actual_saved_gearsets,
        actual_default_index,
        actual_selector_options,
        actual_dropdown_value,
    ) = delete_gearset(
        n_clicks_list,
        gearsets_input,
        initial_default_index,
    )

    # Assertions
    assert actual_saved_gearsets == expected_saved_gearsets
    assert actual_default_index == expected_default_index
    assert actual_selector_options == expected_selector_options
    assert actual_dropdown_value == expected_dropdown_value


@pytest.mark.parametrize(
    "n_clicks_list, triggered_info, initial_saved_gearsets, initial_default_index",
    [
        # 1. No clicks
        (
            [None, None],
            {"type": "gearset-delete", "index": 0},  # Trigger info doesn't matter if no clicks
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 2. Invalid index (out of bounds)
        (
            [None, None, 1],  # Click hypothetical third button
            {"type": "gearset-delete", "index": 2},  # Index 2 is out of bounds
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 3. No triggered_id
        (
            [None, None],
            None,  # No triggered_id
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 4. triggered_id is not a dict
        (
            [1, None],
            "some-other-id",  # Invalid format
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 5. triggered_id has wrong type
        (
            [1, None],
            {"type": "gearset-update", "index": 0},  # Wrong type
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 6. n_clicks for triggered button is None or 0
        (
            [None, None],  # n_clicks is None for index 0
            {"type": "gearset-delete", "index": 0},
            SAVED_GEARSETS_MULTI,
            0,
        ),
        # 7. Empty initial gearsets
        (
            [1],  # Click hypothetical button
            {"type": "gearset-delete", "index": 0},  # Index 0 is out of bounds
            SAVED_GEARSETS_EMPTY,
            None,
        ),
    ],
)
@patch("crit_app.pages.analysis.ctx")  # Mock dash.ctx
def test_delete_gearset_prevent_update(
    mock_ctx,
    n_clicks_list,
    triggered_info,
    initial_saved_gearsets,
    initial_default_index,
):
    """Test the delete_gearset callback function for scenarios causing PreventUpdate."""
    # Configure the mock_ctx
    mock_ctx.triggered_id = triggered_info
    # Simulate the structure of ctx.inputs_list for the ALL pattern matching
    mock_ctx.inputs_list = [
        [
            {"id": {"index": i, "type": "gearset-delete"}, "property": "n_clicks", "value": n_clicks}
            for i, n_clicks in enumerate(n_clicks_list)
        ]
    ]

    # Deep copy initial gearsets
    gearsets_input = [gs.copy() for gs in initial_saved_gearsets]

    # Expect PreventUpdate exception
    with pytest.raises(PreventUpdate):
        delete_gearset(
            n_clicks_list,
            gearsets_input,
            initial_default_index,
        )


# Generate a list of 25 dummy gearsets for testing the limit
SAVED_GEARSETS_LIMIT = [{"name": f"Set {i}"} for i in range(25)]
SAVED_GEARSETS_BELOW_LIMIT = [{"name": f"Set {i}"} for i in range(24)]


@pytest.mark.parametrize(
    "role, gearset_name, main_stat_valid, ten_valid, det_valid, speed_valid, crt_valid, dh_valid, wd_valid, saved_gearsets, expected_disabled",
    [
        # 1. Valid Tank input, below limit
        ("Tank", "My Tank Set", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, False),
        # 2. Valid Healer input, below limit
        ("Healer", "My Healer Set", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, False),
        # 3. Valid Tank input, at limit
        ("Tank", "My Tank Set", True, True, True, True, True, True, True, SAVED_GEARSETS_LIMIT, True),
        # 4. Valid Healer input, at limit
        ("Healer", "My Healer Set", True, True, True, True, True, True, True, SAVED_GEARSETS_LIMIT, True),
        # 5. Missing name
        ("Tank", "", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 6. Whitespace name
        ("Tank", "   ", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 7. Missing role
        (None, "My Set", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 8. Unsupported role
        ("Unsupported", "My Set", True, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 9. Invalid main stat (Tank)
        ("Tank", "My Tank Set", False, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 10. Invalid tenacity (Tank)
        ("Tank", "My Tank Set", True, False, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 11. Invalid determination (Tank)
        ("Tank", "My Tank Set", True, True, False, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 12. Invalid speed (Tank)
        ("Tank", "My Tank Set", True, True, True, False, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 13. Invalid crit (Tank)
        ("Tank", "My Tank Set", True, True, True, True, False, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 14. Invalid dh (Tank)
        ("Tank", "My Tank Set", True, True, True, True, True, False, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 15. Invalid wd (Tank)
        ("Tank", "My Tank Set", True, True, True, True, True, True, False, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 16. Invalid main stat (Healer)
        ("Healer", "My Healer Set", False, True, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 17. Invalid tenacity (Healer) - Should be ignored, button enabled
        ("Healer", "My Healer Set", True, False, True, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, False),
        # 18. Invalid determination (Healer)
        ("Healer", "My Healer Set", True, True, False, True, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 19. Invalid speed (Healer)
        ("Healer", "My Healer Set", True, True, True, False, True, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 20. Invalid crit (Healer)
        ("Healer", "My Healer Set", True, True, True, True, False, True, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 21. Invalid dh (Healer)
        ("Healer", "My Healer Set", True, True, True, True, True, False, True, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 22. Invalid wd (Healer)
        ("Healer", "My Healer Set", True, True, True, True, True, True, False, SAVED_GEARSETS_BELOW_LIMIT, True),
        # 23. Empty gearset list, valid inputs
        ("Tank", "My Tank Set", True, True, True, True, True, True, True, [], False),
        # 24. None gearset list, valid inputs
        ("Tank", "My Tank Set", True, True, True, True, True, True, True, None, False),
    ],
)
def test_validate_save_new_gearset(
    role,
    gearset_name,
    main_stat_valid,
    ten_valid,
    det_valid,
    speed_valid,
    crt_valid,
    dh_valid,
    wd_valid,
    saved_gearsets,
    expected_disabled,
):
    """Test the validate_save_new_gearset callback function."""
    actual_disabled = validate_save_new_gearset(
        role,
        gearset_name,
        main_stat_valid,
        ten_valid,
        det_valid,
        speed_valid,
        crt_valid,
        dh_valid,
        wd_valid,
        saved_gearsets,
    )
    assert actual_disabled == expected_disabled
