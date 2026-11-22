"""Shared SQLite connection management for database operations."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from crit_app_v2.config import DB_URI


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection and close it after its transaction.

    The transaction is committed when the context exits successfully and rolled
    back if an exception leaves the context.

    Yields
    ------
    sqlite3.Connection
        Open connection to the configured application database.
    """
    connection = sqlite3.connect(DB_URI)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
