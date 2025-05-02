from datetime import datetime
from unittest.mock import patch

import pytest

from crit_app.util.history import serialize_analysis_history_record, upsert_local_store_record


@pytest.mark.parametrize(
    "phase,expected_suffix",
    [
        (0, ""),  # No phase suffix for phase 0
        (1, " p1"),  # p1 suffix for phase 1
        (2, " p2"),  # p2 suffix for phase 2
        (3, " p3"),  # p3 suffix for phase 3
    ],
    ids=["phase_0", "phase_1", "phase_2", "phase_3"],
)
def test_serialize_analysis_history_record_phase_naming(phase, expected_suffix):
    """Test that the encounter name correctly includes phase information."""
    # Mock encounter_id_to_short_name to ensure consistent test behavior
    with patch("crit_app.util.history.encounter_id_to_short_name", {123: "TestEncounter"}):
        result = serialize_analysis_history_record(
            analysis_id="test1",
            analysis_scope="Player analysis",
            analysis_datetime=datetime(2025, 4, 26, 10, 0, 0),
            log_datetime=datetime(2025, 4, 25, 9, 0, 0),
            encounter_id=123,
            phase=phase,
            kill_time=600.0,
            job="Dragoon",
            player_name="Test Player",
            analysis_percentile=0.75,
            hierarchy=None,
            hierarchy_id="",
        )

        # Check that the encounter name has the correct phase suffix
        expected_encounter_name = f"TestEncounter{expected_suffix}"
        assert result["encounter_short_name"] == expected_encounter_name


@pytest.mark.parametrize(
    "hierarchy,analysis_id,analysis_scope,job,player_name",
    [
        (None, "test1", "Player analysis", "drg", "Test Player"),
        ("Parent", "test_parent", "Party Analysis", "", ""),
        ("Child", "test_child", "Player analysis", "drg", "Test Player"),
    ],
    ids=["hierarchy_none", "hierarchy_parent", "hierarchy_child"],
)
def test_upsert_local_store_record_empty(hierarchy, analysis_id, analysis_scope, job, player_name):
    """Test that inserting into an empty list works with different hierarchy values."""
    # Initialize empty records
    local_store_records = []

    # Create a new record
    new_record = {
        "analysis_id": analysis_id,
        "analysis_scope": analysis_scope,
        "analysis_datetime": "2025-04-26T10:00:00.000000",
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": job,
        "player_name": player_name,
        "analysis_percentile": 0.75,
        "hierarchy": hierarchy,
        "hierarchy_id": f"{analysis_id}_parent" if hierarchy == "Child" else "",
    }

    # Insert the record
    result = upsert_local_store_record(local_store_records, new_record)

    # Check that the record was added
    assert len(result) == 1
    assert result[0] == new_record
    assert result[0]["hierarchy"] == hierarchy


def test_upsert_local_store_record_insert():
    """Test that inserting a new, non-matching record works."""
    # Initialize with an existing record
    local_store_records = [
        {
            "analysis_id": "existing",
            "analysis_scope": "Player analysis",
            "analysis_datetime": "2025-04-25T09:00:00.000000",
            "log_datetime": "2025-04-24T08:00:00.000000",
            "encounter_short_name": "m5s",
            "kill_time": "09:00",
            "job": "drg",
            "player_name": "Existing Player",
            "analysis_percentile": 0.80,
            "hierarchy": None,
            "hierarchy_id": "",
        }
    ]

    # Create a new record that doesn't match existing
    new_record = {
        "analysis_id": "test1",
        "analysis_scope": "Player analysis",
        "analysis_datetime": "2025-04-26T10:00:00.000000",
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": "drg",
        "player_name": "Test Player",
        "analysis_percentile": 0.75,
        "hierarchy": None,
        "hierarchy_id": "",
    }

    # Insert the record
    result = upsert_local_store_record(local_store_records, new_record)

    # Check that the record was added
    assert len(result) == 2
    assert result[1] == new_record
    assert result[0]["analysis_id"] == "existing"  # Ensure original record still exists


def test_upsert_local_store_record_insert_different_hierarchy():
    """Test that inserting a record with identical data except for hierarchy results in insert, not update."""
    # Initial record with None hierarchy
    existing_record = {
        "analysis_id": "test1",
        "analysis_scope": "Player analysis",
        "analysis_datetime": "2025-04-26T10:00:00.000000",
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": "drg",
        "player_name": "Test Player",
        "analysis_percentile": 0.75,
        "hierarchy": None,
        "hierarchy_id": "",
    }

    local_store_records = [existing_record]

    # New record with same data but different hierarchy
    new_record = dict(existing_record)
    new_record["hierarchy"] = "Child"
    new_record["hierarchy_id"] = "test1_parent"

    # Insert the record
    result = upsert_local_store_record(local_store_records, new_record)

    # Check that both records exist now (insert, not update)
    assert len(result) == 2
    # Original record should still be there with None hierarchy
    assert any(r["hierarchy"] is None for r in result)
    # New record should be added with Child hierarchy
    assert any(r["hierarchy"] == "Child" for r in result)


def test_upsert_local_store_record_update():
    """Test that updating an existing record works."""
    # Initialize with an existing record
    old_record = {
        "analysis_id": "test1",
        "analysis_scope": "Player analysis",
        "analysis_datetime": "2025-04-26T10:00:00.000000",
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": "drg",
        "player_name": "Test Player",
        "analysis_percentile": 0.75,
        "hierarchy": None,
        "hierarchy_id": "",
    }

    local_store_records = [old_record]

    # Same key tuple but updated percentile
    updated_record = dict(old_record)
    updated_record["analysis_percentile"] = 0.85

    # Update the record
    result = upsert_local_store_record(local_store_records, updated_record)

    # Check that the record was updated
    assert len(result) == 1
    assert result[0]["analysis_percentile"] == 0.85


def test_upsert_local_store_record_preserve_analysis_datetime():
    """Test that preserve_analysis_datetime parameter keeps the original analysis_datetime when updating."""
    # Create initial record with a specific analysis datetime
    old_datetime = "2025-04-26T10:00:00.000000"
    old_record = {
        "analysis_id": "test1",
        "analysis_scope": "Player analysis",
        "analysis_datetime": old_datetime,
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": "drg",
        "player_name": "Test Player",
        "analysis_percentile": 0.75,
        "hierarchy": None,
        "hierarchy_id": "",
    }

    local_store_records = [old_record]

    # New record with updated datetime and percentile
    new_datetime = "2025-04-27T11:00:00.000000"
    updated_record = dict(old_record)
    updated_record["analysis_datetime"] = new_datetime
    updated_record["analysis_percentile"] = 0.85

    # Test 1: Default behavior - analysis_datetime should be updated
    result1 = upsert_local_store_record(local_store_records.copy(), updated_record)
    assert result1[0]["analysis_datetime"] == new_datetime
    assert result1[0]["analysis_percentile"] == 0.85

    # Test 2: With preserve_analysis_datetime=True - analysis_datetime should NOT be updated
    result2 = upsert_local_store_record(local_store_records.copy(), updated_record, preserve_analysis_datetime=True)
    assert result2[0]["analysis_datetime"] == old_datetime  # Should keep old datetime
    assert result2[0]["analysis_percentile"] == 0.85  # But should update other fields


def test_upsert_local_store_record_preserve_analysis_datetime_with_insert():
    """Test that preserve_analysis_datetime parameter doesn't affect new records."""
    # Initialize with an existing record
    local_store_records = [
        {
            "analysis_id": "existing",
            "analysis_scope": "Player analysis",
            "analysis_datetime": "2025-04-25T09:00:00.000000",
            "log_datetime": "2025-04-24T08:00:00.000000",
            "encounter_short_name": "m5s",
            "kill_time": "09:00",
            "job": "drg",
            "player_name": "Existing Player",
            "analysis_percentile": 0.80,
            "hierarchy": None,
            "hierarchy_id": "",
        }
    ]

    # Create a new record that doesn't match existing
    new_record = {
        "analysis_id": "test1",
        "analysis_scope": "Player analysis",
        "analysis_datetime": "2025-04-26T10:00:00.000000",
        "log_datetime": "2025-04-25T09:00:00.000000",
        "encounter_short_name": "m5s",
        "kill_time": "10:00",
        "job": "drg",
        "player_name": "Test Player",
        "analysis_percentile": 0.75,
        "hierarchy": None,
        "hierarchy_id": "",
    }

    # Insert the record with preserve_analysis_datetime=True
    result = upsert_local_store_record(local_store_records, new_record, preserve_analysis_datetime=True)

    # Check that the new record was added with its original datetime (preserve flag shouldn't affect new records)
    assert len(result) == 2
    assert result[1]["analysis_datetime"] == "2025-04-26T10:00:00.000000"
    assert result[1]["analysis_percentile"] == 0.75
