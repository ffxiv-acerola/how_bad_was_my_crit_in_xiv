"""Tests for database and blob-store setup operations."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from crit_app_v2.db import setup
from crit_app_v2.db.schema import CREATE_TABLE_STATEMENTS


def test_initialize_database_creates_tables_and_blob_directories(
    tmp_path: Path,
) -> None:
    """Initialization creates all schema tables and expected blob directories."""
    db_uri = tmp_path / "data" / "reports.db"
    blob_uri = tmp_path / "blobs"

    setup.initialize_database(db_uri, blob_uri)

    with closing(sqlite3.connect(db_uri)) as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type = 'table'")}

    assert len(CREATE_TABLE_STATEMENTS) == 7
    assert tables == {
        "encounter",
        "report",
        "party_report",
        "creation_player_analysis",
        "access",
        "error_player_analysis",
        "error_party_analysis",
    }
    assert (blob_uri / "job-rotation-clippings").is_dir()
    assert (blob_uri / "party-analyses").is_dir()
    assert (blob_uri / "error-logs").is_dir()


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    """Repeated schema creation completes without duplicating tables."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"

    setup.initialize_database(db_uri, blob_uri)
    setup.initialize_database(db_uri, blob_uri)

    with closing(sqlite3.connect(db_uri)) as connection:
        table_count = connection.execute("select count(*) from sqlite_master where type = 'table'").fetchone()[0]

    assert table_count == 7


def test_main_creates_a_missing_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The setup command initializes the database and blobs when neither exists."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"
    monkeypatch.setattr(setup, "DB_URI", db_uri)
    monkeypatch.setattr(setup, "BLOB_URI", blob_uri)

    exit_code = setup.main([])

    assert exit_code == 0
    assert db_uri.is_file()
    assert (blob_uri / "error-logs").is_dir()


def test_main_does_nothing_if_database_already_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An existing database makes the setup command a no-op."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"
    blob_uri.mkdir()
    existing_blob = blob_uri / "cached-analysis.pkl"
    existing_blob.write_text("keep this")
    with closing(sqlite3.connect(db_uri)) as connection:
        _ = connection.execute("create table prior_data (value text)")
        connection.commit()
    monkeypatch.setattr(setup, "DB_URI", db_uri)
    monkeypatch.setattr(setup, "BLOB_URI", blob_uri)

    exit_code = setup.main([])

    assert exit_code == 0
    assert existing_blob.read_text() == "keep this"
    with closing(sqlite3.connect(db_uri)) as connection:
        assert connection.execute("select name from sqlite_master where name = 'prior_data'").fetchone() == (
            "prior_data",
        )
        assert connection.execute("select name from sqlite_master where name = 'encounter'").fetchone() is None


def test_main_does_nothing_if_blob_path_already_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An existing blob path makes the setup command a no-op."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"
    blob_uri.mkdir()
    monkeypatch.setattr(setup, "DB_URI", db_uri)
    monkeypatch.setattr(setup, "BLOB_URI", blob_uri)

    exit_code = setup.main([])

    assert exit_code == 0
    assert not db_uri.exists()
    assert blob_uri.is_dir()


def test_delete_setup_removes_database_sidecars_and_blobs(tmp_path: Path) -> None:
    """Delete removes the SQLite files and the entire blob directory."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"
    database_files = (
        db_uri,
        Path(f"{db_uri}-journal"),
        Path(f"{db_uri}-wal"),
        Path(f"{db_uri}-shm"),
    )
    for path in database_files:
        path.write_text("database file")
    blob_file = blob_uri / "cached-analysis.pkl"
    blob_file.parent.mkdir()
    blob_file.write_text("blob")

    setup.delete_setup(db_uri, blob_uri)

    assert not db_uri.exists()
    assert all(not path.exists() for path in database_files)
    assert not blob_uri.exists()


def test_main_deletes_setup_with_delete_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The explicit delete option removes both database and blob paths."""
    db_uri = tmp_path / "reports.db"
    blob_uri = tmp_path / "blobs"
    db_uri.write_text("database")
    blob_uri.mkdir()
    (blob_uri / "cached-analysis.pkl").write_text("blob")
    monkeypatch.setattr(setup, "DB_URI", db_uri)
    monkeypatch.setattr(setup, "BLOB_URI", blob_uri)

    exit_code = setup.main(["--delete"])

    assert exit_code == 0
    assert not db_uri.exists()
    assert not blob_uri.exists()
