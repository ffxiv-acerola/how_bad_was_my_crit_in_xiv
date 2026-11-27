"""Database insertion functions for analysis errors."""

import datetime
from collections.abc import Sequence
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from crit_app_v2.db.connection import get_connection


class PlayerAnalysisErrorRecord(BaseModel):
    """Validated error details for a failed player analysis."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    report_id: str
    fight_id: int
    player_id: int
    encounter_id: int
    encounter_name: str
    phase_id: int
    job: str
    player_name: str
    main_stat_pre_bonus: int
    main_stat: int
    main_stat_type: str
    secondary_stat_pre_bonus: int | None
    secondary_stat: int | None
    secondary_stat_type: str | None
    determination: int
    speed: int
    critical_hit: int
    direct_hit: int
    weapon_damage: int
    delay: float
    medication_amount: int
    party_bonus: float
    error_message: str
    traceback: str

    def to_row(self) -> tuple[object, ...]:
        """Map the error record to the player-error table column order."""
        return (
            f"pl-{self.report_id}-{self.fight_id}.{self.phase_id}.{self.player_id}",
            self.report_id,
            self.fight_id,
            self.player_id,
            self.encounter_id,
            self.encounter_name,
            self.phase_id,
            self.job,
            self.player_name,
            self.main_stat_pre_bonus,
            self.main_stat,
            self.main_stat_type,
            self.secondary_stat_pre_bonus,
            self.secondary_stat,
            self.secondary_stat_type,
            self.determination,
            self.speed,
            self.critical_hit,
            self.direct_hit,
            self.weapon_damage,
            self.delay,
            self.medication_amount,
            self.party_bonus,
            self.error_message,
            self.traceback,
            datetime.datetime.now().isoformat(),
            1,
        )


def insert_error_player_analysis(record: PlayerAnalysisErrorRecord) -> None:
    """Insert a validated player-analysis failure into the error table."""
    sql_query = """
    INSERT OR REPLACE INTO error_player_analysis (
        error_id, report_id, fight_id, player_id, encounter_id, encounter_name,
        phase_id, job, player_name, main_stat_pre_bonus, main_stat,
        main_stat_type, secondary_stat_pre_bonus, secondary_stat,
        secondary_stat_type, determination, speed, critical_hit, direct_hit,
        weapon_damage, delay, medication_amount, party_bonus, error_message,
        traceback, error_ts, error_active
    ) VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )
    """

    with get_connection() as con:
        cur = con.cursor()
        cur.execute(sql_query, record.to_row())


def insert_error_party_analysis(
    report_id: str,
    fight_id: int,
    fight_phase: int,
    encounter_id: int,
    job: list[str],
    player_name: list[str],
    player_id: list[int],
    main_stat_no_buff: list[int],
    secondary_stat_no_buff: list[int | str | None],
    determination: list[int],
    speed: list[int],
    crit: list[int],
    dh: list[int],
    weapon_damage: list[int],
    main_stat_multiplier: list[float],
    medication_amt: int,
    etro_url: list[str],
    error_message: str,
    error_traceback: str,
) -> None:
    """Insert error analysis information for party into database.

    Args:
        report_id (str): FFLogs report identifier
        fight_id (int): Fight ID within report
        fight_phase (int): Phase ID within fight
        encounter_id (int): Encounter ID
        job (list[str]): List of player jobs/classes
        player_name (list[str]): List of player names
        player_id (list[int]): List of player IDs
        main_stat_no_buff (list[int]): List of main stat values without buffs
        secondary_stat_no_buff (list[int | str | None]): List of secondary stat values
        determination (list[int]): List of determination stat values
        speed (list[int]): List of speed stat values
        crit (list[int]): List of critical hit stat values
        dh (list[int]): List of direct hit stat values
        weapon_damage (list[int]): List of weapon damage values
        main_stat_multiplier (list[float]): List of main stat multipliers
        etro_url (list[str]): List of build URLs, empty for no URL.
        medication_amt (int): Medicine/food bonus
        error_message (str): Error message
        error_traceback (str): Error traceback
    """
    sql_query = """
    INSERT OR REPLACE INTO error_party_analysis VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )
    """

    # format into 8 rows
    rows_to_insert: list[Sequence[Any]] = []
    error_ts = datetime.datetime.now()

    for a in range(len(player_name)):
        rows_to_insert.append(
            (
                f"pa-{report_id}-{fight_id}.{fight_phase}.{player_id[a]}",
                report_id,
                fight_id,
                fight_phase,
                encounter_id,
                job[a].upper(),
                player_name[a],
                player_id[a],
                main_stat_no_buff[a],
                None
                if secondary_stat_no_buff[a] == "None"
                else secondary_stat_no_buff[a],
                determination[a],
                speed[a],
                crit[a],
                dh[a],
                weapon_damage[a],
                main_stat_multiplier,
                medication_amt,
                None if etro_url[a] == "" else etro_url[a],
                error_message,
                error_traceback,
                error_ts,
                1,
            )
        )
    with get_connection() as con:
        cur = con.cursor()
        cur.executemany(sql_query, rows_to_insert)
