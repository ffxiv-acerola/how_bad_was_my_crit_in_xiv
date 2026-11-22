"""Shared SQLite connection management for database operations."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from crit_app_v2.config import DB_URI


@contextmanager
def get_connection(
    database_uri: Path | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection and close it after its transaction.

    The transaction is committed when the context exits successfully and rolled
    back if an exception leaves the context.

    Parameters
    ----------
    database_uri : pathlib.Path, optional
        Database path override. Defaults to the configured application database.

    Yields
    ------
    sqlite3.Connection
        Open connection to the configured application database.
    """
    connection = sqlite3.connect(database_uri if database_uri is not None else DB_URI)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
