"""Persistence mapping and queries for FFLogs encounter records."""

from ast import literal_eval
from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import AnyHttpUrl

from crit_app_v2.db.connection import get_connection
from crit_app_v2.fflogs_encounters.models import (
    Encounter,
    EncounterPersonnel,
    EncounterUrl,
)


def _id_list_to_db(value: list[int] | None) -> str | None:
    """Serialize an optional ID list in the format used by the legacy schema."""
    return repr(value) if value is not None else None


def _id_list_from_db(value: str | None) -> list[int] | None:
    """Parse an optional ID list stored as a Python literal."""
    if value is None:
        return None
    parsed = literal_eval(value)
    if not isinstance(parsed, list) or any(type(item) is not int for item in parsed):
        raise ValueError("Stored encounter IDs must be a list of integers.")
    return parsed


def encounter_to_db_rows(encounter: Encounter) -> list[tuple[Any, ...]]:
    """Map an encounter and its players to rows matching the encounter table.

    Parameters
    ----------
    encounter
        Validated FFLogs encounter to persist.

    Returns
    -------
    list[tuple[Any, ...]]
        One 13-column database row for each playable player. Limit Break is
        intentionally omitted until party analysis persistence is implemented.
    """
    report_id = encounter.encounter_url.report_id
    fight_id = encounter.fight_id_resolved
    return [
        (
            report_id,
            fight_id,
            encounter.encounter_id,
            encounter.last_phase_index,
            encounter.encounter_name,
            encounter.kill_time,
            player.player_name,
            player.player_server,
            player.player_id,
            _id_list_to_db(player.pet_ids),
            _id_list_to_db(encounter.excluded_enemy_ids),
            player.job.value,
            player.role.value,
        )
        for player in encounter.players
    ]


def update_encounter_table(db_rows: Iterable[Sequence[Any]]) -> None:
    """Upsert encounter rows supplied by an existing persistence workflow.

    New player-analysis code should prefer :func:`save_encounter`, which maps
    the validated model and replaces the complete fight roster atomically.

    Parameters
    ----------
    db_rows
        Rows in encounter-table column order.
    """
    with get_connection() as connection:
        _ = connection.executemany(
            """
            INSERT OR REPLACE INTO encounter
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            db_rows,
        )


def save_encounter(encounter: Encounter) -> None:
    """Replace all stored rows for an encounter in one database transaction.

    Deleting the existing roster before inserting the new one prevents stale
    participants when the FFLogs roster changes between fetches.

    Parameters
    ----------
    encounter
        Validated encounter fetched from FFLogs on the server.
    """
    rows = encounter_to_db_rows(encounter)
    report_id = encounter.encounter_url.report_id
    fight_id = encounter.fight_id_resolved

    with get_connection() as connection:
        _ = connection.execute(
            "DELETE FROM encounter WHERE report_id = ? AND fight_id = ?",
            (report_id, fight_id),
        )
        if rows:
            _ = connection.executemany(
                """
                INSERT INTO encounter VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )


def load_encounter(report_id: str, fight_id: int) -> Encounter | None:
    """Load a previously fetched encounter from the database.

    Parameters
    ----------
    report_id
        FFLogs report identifier.
    fight_id
        Resolved numeric fight identifier.

    Returns
    -------
    Encounter or None
        The stored encounter and roster, or ``None`` if no player rows exist.

    Raises
    ------
    ValueError
        If rows disagree about fight metadata or contain malformed ID lists.
    pydantic.ValidationError
        If persisted values cannot form a valid encounter model.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                encounter_id,
                last_phase_index,
                encounter_name,
                kill_time,
                player_name,
                player_server,
                player_id,
                pet_ids,
                excluded_enemy_ids,
                job,
                role
            FROM encounter
            WHERE report_id = ? AND fight_id = ?
            ORDER BY player_id
            """,
            (report_id, fight_id),
        )
        columns = [column[0] for column in cursor.description or ()]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if not rows:
        return None

    shared_columns = (
        "encounter_id",
        "last_phase_index",
        "encounter_name",
        "kill_time",
        "excluded_enemy_ids",
    )
    first_row = rows[0]
    if any(
        any(row[column] != first_row[column] for column in shared_columns)
        for row in rows[1:]
    ):
        raise ValueError("Stored encounter rows disagree about fight metadata.")

    personnel = [
        EncounterPersonnel(
            player_name=row["player_name"],
            player_server=row["player_server"],
            player_id=row["player_id"],
            pet_ids=_id_list_from_db(row["pet_ids"]),
            job=row["job"],
            role=row["role"],
        )
        for row in rows
    ]
    encounter_url = EncounterUrl(
        build_url=AnyHttpUrl(
            f"https://www.fflogs.com/reports/{report_id}?fight={fight_id}"
        )
    )
    return Encounter(
        encounter_url=encounter_url,
        fight_id_resolved=fight_id,
        encounter_id=first_row["encounter_id"],
        encounter_name=first_row["encounter_name"],
        last_phase_index=first_row["last_phase_index"],
        kill_time=first_row["kill_time"],
        excluded_enemy_ids=_id_list_from_db(first_row["excluded_enemy_ids"]),
        players=personnel,
        limit_break=None,
    )


def get_player_analysis_job_records(
    report_id: str, fight_id: int
) -> list[dict[str, Any]]:
    """Retrieve stored player records for a fight.

    Limit Break rows are not stored by the player-analysis workflow.

    Parameters
    ----------
    report_id
        FFLogs report identifier.
    fight_id
        Fight identifier within the report.

    Returns
    -------
    list[dict[str, Any]]
        Player records keyed by column name.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT player_name, player_id, job, role
            FROM encounter
            WHERE report_id = ? AND fight_id = ?
                AND role != 'Limit Break'
            ORDER BY player_id
            """,
            (report_id, fight_id),
        )
        columns = [column[0] for column in cursor.description or ()]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_party_analysis_calculation_info(
    report_id: str, fight_id: int
) -> tuple[int | None, int | None, dict[int, list[int] | None] | None]:
    """Retrieve encounter and pet identifiers for a party analysis.

    Parameters
    ----------
    report_id
        FFLogs report identifier.
    fight_id
        Fight identifier within the report.

    Returns
    -------
    tuple[int | None, int | None, dict[int, list[int] | None] | None]
        Encounter ID, Limit Break player ID, and player-to-pet-ID mapping.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT encounter_id, job, player_id, pet_ids
            FROM encounter
            WHERE report_id = ? AND fight_id = ?
            """,
            (report_id, fight_id),
        )
        rows = cursor.fetchall()

    if not rows:
        return None, None, None

    encounter_id = rows[0][0]
    limit_break_ids = [row[2] for row in rows if row[1] == "LimitBreak"]
    limit_break_id = limit_break_ids[0] if limit_break_ids else None
    pet_ids = {row[2]: _id_list_from_db(row[3]) for row in rows}
    return encounter_id, limit_break_id, pet_ids
