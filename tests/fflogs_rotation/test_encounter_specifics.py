import pandas as pd
import pytest

from fflogs_rotation.encounter_specifics import EncounterSpecifics


@pytest.mark.parametrize(
    "test_id,elapsed_time,ability_name,initial_target_id,blooming_abomination_id,expected_target_id",
    [
        # Early blooming abomination entries (should be converted to negative)
        (26, 71.865, "Water II in Blue", 425, 425, -425),
        (27, 71.865, "Water II in Blue", 425, 425, -425),
        (29, 74.358, "Fire II in Red", 425, 425, -425),
        (31, 79.395, "Water II in Blue", 425, 425, -425),
        (32, 79.395, "Water II in Blue", 425, 425, -425),
        (35, 80.953, "Holy in White", 425, 425, -425),
        (39, 83.852, "Holy in White", 425, 425, -425),
        # Late blooming abomination entries (should remain positive)
        (180, 510.504, "Rainbow Drip", 425, 425, 425),
        (182, 510.504, "Rainbow Drip", 425, 425, 425),
        (183, 510.504, "Rainbow Drip", 425, 425, 425),
        (184, 512.998, "Comet in Black", 425, 425, 425),
        # Non-abomination entries (should not change)
        (100, 75.0, "Other Ability", 100, 425, 100),
        (101, 150.0, "Other Ability", 100, 425, 100),
        (102, 250.0, "Other Ability", 100, 425, 100),
        (103, 450.0, "Other Ability", 100, 425, 100),
    ],
)
def test_m7s_exclude_final_blooming(
    test_id, elapsed_time, ability_name, initial_target_id, blooming_abomination_id, expected_target_id
):
    """Test that m7s_exclude_final_blooming correctly marks targetIDs.

    This parameterized test validates that:
    1. Early blooming abomination IDs (before 200s) are made negative
    2. Late blooming abomination IDs (after 200s) remain positive
    3. Non-abomination IDs are not modified
    """
    # Create a DataFrame with a single row for each test case
    data = {
        "elapsed_time": [elapsed_time],
        "ability_name": [ability_name],
        "targetID": [initial_target_id],
    }

    # Create test DataFrame with the specified index
    actions_df = pd.DataFrame(data, index=[test_id])

    # Apply the function
    encounter_specifics = EncounterSpecifics()
    result_df = encounter_specifics.m7s_exclude_final_blooming(
        actions_df, blooming_abomination_game_id=blooming_abomination_id
    )

    # Check the result for this specific row
    assert result_df.loc[test_id, "targetID"] == expected_target_id, (
        f"Row {test_id}: {ability_name} at {elapsed_time}s with initial targetID={initial_target_id} "
        f"should have targetID={expected_target_id} after processing"
    )
