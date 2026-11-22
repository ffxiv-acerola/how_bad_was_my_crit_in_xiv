"""Initialize or delete the v2 application database and blob store."""

import argparse
import shutil
from collections.abc import Sequence
from pathlib import Path

from crit_app_v2.config import BLOB_URI, DB_URI
from crit_app_v2.db.connection import get_connection
from crit_app_v2.db.schema import create_tables

_BLOB_SUBDIRECTORIES = (
    "job-rotation-clippings",
    "party-analyses",
    "error-logs",
)


def create_blob_directories(blob_uri: Path = BLOB_URI) -> None:
    """Create the blob root and its application subdirectories.

    Parameters
    ----------
    blob_uri : pathlib.Path
        Root path for cached analysis files.
    """
    blob_uri.mkdir(parents=True, exist_ok=True)
    for subdirectory in _BLOB_SUBDIRECTORIES:
        (blob_uri / subdirectory).mkdir(parents=True, exist_ok=True)


def initialize_database(
    db_uri: Path = DB_URI,
    blob_uri: Path = BLOB_URI,
) -> None:
    """Create the database parent, tables, and blob directory structure.

    Parameters
    ----------
    db_uri : pathlib.Path
        SQLite database path.
    blob_uri : pathlib.Path
        Root path for cached analysis files.
    """
    db_uri.parent.mkdir(parents=True, exist_ok=True)
    create_blob_directories(blob_uri)
    with get_connection(db_uri) as connection:
        create_tables(connection)


def _remove_path(path: Path) -> None:
    """Remove a file, directory tree, or symlink at the specified path."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _database_paths(db_uri: Path) -> tuple[Path, ...]:
    """Return the database path and its known SQLite sidecar paths."""
    return (
        db_uri,
        Path(f"{db_uri}-journal"),
        Path(f"{db_uri}-wal"),
        Path(f"{db_uri}-shm"),
    )


def delete_setup(
    db_uri: Path = DB_URI,
    blob_uri: Path = BLOB_URI,
) -> None:
    """Delete the database, SQLite sidecars, and all cached blob data.

    Parameters
    ----------
    db_uri : pathlib.Path
        SQLite database path.
    blob_uri : pathlib.Path
        Root path for cached analysis files. Its contents are deleted.
    """
    for database_path in _database_paths(db_uri):
        _remove_path(database_path)
    _remove_path(blob_uri)


def has_existing_setup(
    db_uri: Path = DB_URI,
    blob_uri: Path = BLOB_URI,
) -> bool:
    """Return whether either configured setup path already exists.

    Parameters
    ----------
    db_uri : pathlib.Path
        SQLite database path.
    blob_uri : pathlib.Path
        Root path for cached analysis files.

    Returns
    -------
    bool
        Whether the database path or blob-store path exists.
    """
    return any(path.exists() for path in _database_paths(db_uri)) or blob_uri.exists()


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for database maintenance operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--delete",
        action="store_true",
        help="delete the database and all blob data",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Create a missing setup or delete it when explicitly requested.

    Parameters
    ----------
    argv : sequence of str or None, optional
        Command-line arguments. Defaults to the process arguments.

    Returns
    -------
    int
        Process exit status, zero on success.
    """
    args = _build_parser().parse_args(argv)

    if args.delete:
        delete_setup(DB_URI, BLOB_URI)
        print("Database and blob data deleted.")
        return 0

    if has_existing_setup(DB_URI, BLOB_URI):
        print("Database or blob path already exists; no changes made.")
        return 0

    initialize_database(DB_URI, BLOB_URI)
    print("Database tables and blob directories created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
