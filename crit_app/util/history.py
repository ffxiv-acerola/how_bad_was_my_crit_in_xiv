from datetime import datetime

from crit_app.job_data.encounter_data import encounter_id_to_short_name
from crit_app.job_data.roles import abbreviated_job_map
from crit_app.shared_elements import format_kill_time_str


def serialize_analysis_history_record(
    analysis_id: str,
    analysis_scope: str,
    analysis_datetime: datetime,
    log_datetime: datetime,
    encounter_id: int,
    phase: int,
    kill_time: float,
    job: str,
    player_name: str,
    analysis_percentile: float,
    hierarchy: str,
    hierarchy_id: str,
) -> dict[str, str | float]:
    """
    Converts analysis record data into a serialized form suitable for frontend display or storage.

    This function transforms raw analysis data by formatting datetime and kill time,
    converting encounter_id to a human-readable short name using the encounter_id_to_short_name
    mapping, and abbreviating job names.

    Args:
        analysis_id: Unique identifier for the analysis
        analysis_scope: Type of analysis (e.g., 'Player analysis', 'Party Analysis')
        analysis_datetime: When the analysis was performed
        encounter_id: Numeric identifier for the encounter
        kill_time: Duration of the encounter in seconds
        job: Full job name (e.g., 'Dragoon', 'Scholar')
        player_name: Character name
        analysis_percentile: Analysis result as a percentile (0.0-1.0)
        hierarchy: Relationship between analyses (e.g., 'Parent', 'Child', None)

    Returns:
        A dictionary containing formatted and serialized analysis data
    """
    encounter_short_name = encounter_id_to_short_name.get(encounter_id, "")
    if phase > 0:
        encounter_short_name += f" p{phase}"

    record = {
        "analysis_id": analysis_id,
        "analysis_scope": analysis_scope,
        "analysis_datetime": analysis_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "log_datetime": log_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "encounter_short_name": encounter_short_name,
        "kill_time": format_kill_time_str(kill_time),
        "job": abbreviated_job_map.get(job, ""),
        "player_name": player_name,
        "analysis_percentile": analysis_percentile,
        "hierarchy": hierarchy,
        "hierarchy_id": hierarchy_id,
    }
    return record


def upsert_local_store_record(
    local_store_records: list[dict[str, str | float]],
    new_record: dict[str, str | float],
    preserve_analysis_datetime: bool = False,
) -> list[dict[str, str | float]]:
    """
    Updates an existing record or inserts a new record into the local store records list.

    Records are matched based on a composite key of (analysis_id, hierarchy).
    If a matching record is found, it is updated with the new record data.
    If no matching record is found, the new record is appended to the list.

    Args:
        local_store_records: A list of existing analysis history records
        new_record: The record to insert or update
        preserve_analysis_datetime: If True, keeps the original analysis_datetime
                                   when updating an existing record

    Returns:
        The updated list of records
    """
    if local_store_records is None:
        local_store_records = []
    new_key = (new_record["analysis_id"], new_record["hierarchy"])
    for i, record in enumerate(local_store_records):
        existing_key = (record["analysis_id"], record["hierarchy"])
        if existing_key == new_key:
            if preserve_analysis_datetime and "analysis_datetime" in record:
                # Create a copy of the new record but keep the original analysis_datetime
                updated_record = new_record.copy()
                updated_record["analysis_datetime"] = record["analysis_datetime"]
                local_store_records[i] = updated_record
            else:
                local_store_records[i] = new_record
            return local_store_records
    local_store_records.append(new_record)
    return local_store_records
