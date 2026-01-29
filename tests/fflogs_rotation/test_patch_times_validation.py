import pytest

from crit_app.job_data.encounter_data import patch_times
from fflogs_rotation.actions import ActionTable

# Group the patch dictionaries for easy parametrization
PATCH_DICTS = [
    ("Global", patch_times),
    # ("CN", patch_times_cn),
    # ("KO", patch_times_ko),
]


@pytest.mark.parametrize("region, patch_dict", PATCH_DICTS)
def test_patch_keys_ordered(region, patch_dict):
    """Verify patch keys (versions) are strictly increasing."""
    keys = list(patch_dict.keys())
    assert keys == sorted(keys), f"{region}: Patch versions are not in increasing order"


@pytest.mark.parametrize("region, patch_dict", PATCH_DICTS)
def test_patch_times_internal_consistency(region, patch_dict):
    """Verify each patch's start time is before its end time."""
    for patch, times in patch_dict.items():
        assert (
            times["start"] < times["end"]
        ), f"{region} Patch {patch}: Start time {times['start']} is not before end time {times['end']}"


@pytest.mark.parametrize("region, patch_dict", PATCH_DICTS)
def test_patch_continuity_and_ordering(region, patch_dict):
    """
    Verify patches are sequential in time and effectively adjacent.

    Checks that:
    1. Patch N start > Patch N-1 end (No overlapping)
    2. Gap between Patch N-1 end and Patch N start is <= 1ms (Adjacency)
    """
    # Sort by patch version to ensure we check in order
    sorted_patches = sorted(patch_dict.items())

    for i in range(1, len(sorted_patches)):
        prev_patch, prev_data = sorted_patches[i - 1]
        curr_patch, curr_data = sorted_patches[i]

        # Check for monotonicity / no overlap
        assert (
            curr_data["start"] > prev_data["end"]
        ), f"{region}: Patch {curr_patch} starts ({curr_data['start']}) before or at Patch {prev_patch} ends ({prev_data['end']})"

        # Check adjacency (gap <= 1ms)
        # Expected: curr_start == prev_end + 1
        gap = curr_data["start"] - prev_data["end"]
        assert gap <= 1, f"{region}: Gap between Patch {prev_patch} and {curr_patch} is {gap}ms (should be <= 1ms)"


@pytest.mark.parametrize(
    "region_code, patch_dict",
    [
        ("NA", patch_times),  # Global includes NA
        ("EU", patch_times),  # Global includes EU
        ("JP", patch_times),  # Global includes JP
        ("OC", patch_times),  # Global includes OC
        # ("CN", patch_times_cn),
        # ("KR", patch_times_ko),
    ],
)
def test_get_patch_number_lookup(region_code, patch_dict):
    """Test standard lookup behavior for _get_patch_number."""
    for patch, times in patch_dict.items():
        # Test middle of range
        mid_time = (times["start"] + times["end"]) // 2
        result = ActionTable._get_patch_number(mid_time, region_code)
        assert result == patch, f"Region {region_code}: Expected {patch} for time {mid_time}, got {result}"


@pytest.mark.parametrize(
    "region_code, patch_dict",
    [
        ("NA", patch_times),
        # ("CN", patch_times_cn),
        # ("KR", patch_times_ko),
    ],
)
def test_get_patch_number_boundaries(region_code, patch_dict):
    """Test boundary conditions (exact start/end times)."""
    for patch, times in patch_dict.items():
        # Test exact start
        result_start = ActionTable._get_patch_number(times["start"], region_code)
        assert (
            result_start == patch
        ), f"Region {region_code}: Expected {patch} at start time {times['start']}, got {result_start}"

        # Test exact end
        result_end = ActionTable._get_patch_number(times["end"], region_code)
        assert (
            result_end == patch
        ), f"Region {region_code}: Expected {patch} at end time {times['end']}, got {result_end}"
