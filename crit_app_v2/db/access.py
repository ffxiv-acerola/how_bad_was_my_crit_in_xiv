"""Database updates for analysis access tracking."""

import datetime

from crit_app_v2.db.connection import get_connection


def update_access_table(db_row: tuple[str, datetime.datetime]) -> None:
    """
    Update access table, keeping track of when and how much an analysis ID is accessed.

    Inputs:
        db_row - tuple, of row to insert. Contains (`analysis_id`, `access_datetime`).
    """
    with get_connection() as con:
        cur = con.cursor()
        cur.execute(
            """
        insert into access
        values (?, ?)
        """,
            db_row,
        )
