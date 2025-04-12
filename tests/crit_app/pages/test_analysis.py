from unittest.mock import patch

import pytest
from dash.exceptions import PreventUpdate

from crit_app.job_data.encounter_data import (
    stat_ranges,
)

# Mock dash.register_page at the module level, before importing
# This prevents the PageError during import
with patch("dash.register_page"):
    # Now it's safe to import the modules
    from crit_app.pages.analysis import (
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
