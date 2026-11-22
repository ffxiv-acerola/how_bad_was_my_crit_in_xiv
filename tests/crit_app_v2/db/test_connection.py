"""Tests for the shared database connection context manager."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import cast

import pytest

from crit_app_v2.db import connection


def test_get_connection_commits_and_closes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Successful connection scopes commit work and close the connection."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)

    scoped_connection: sqlite3.Connection | None = None
    with connection.get_connection() as db_connection:
        scoped_connection = db_connection
        _ = db_connection.execute("create table item (value text)")
        _ = db_connection.execute("insert into item values (?)", ("saved",))

    with closing(sqlite3.connect(database_path)) as verification_connection:
        row = cast(
            tuple[str] | None,
            verification_connection.execute("select value from item").fetchone(),
        )

    assert row == ("saved",)
    assert scoped_connection is not None
    with pytest.raises(sqlite3.ProgrammingError):
        _ = scoped_connection.execute("select 1")


def test_get_connection_rolls_back_and_closes_on_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Exceptional connection scopes roll back work and still close the connection."""
    database_path = tmp_path / "test.db"
    monkeypatch.setattr(connection, "DB_URI", database_path)
    with closing(sqlite3.connect(database_path)) as setup_connection:
        _ = setup_connection.execute("create table item (value text)")

    scoped_connection: sqlite3.Connection | None = None
    with pytest.raises(ValueError, match="test failure"):
        with connection.get_connection() as db_connection:
            scoped_connection = db_connection
            _ = db_connection.execute("insert into item values (?)", ("discarded",))
            raise ValueError("test failure")

    with closing(sqlite3.connect(database_path)) as verification_connection:
        rows = verification_connection.execute("select value from item").fetchall()

    assert rows == []
    assert scoped_connection is not None
    with pytest.raises(sqlite3.ProgrammingError):
        _ = scoped_connection.execute("select 1")
