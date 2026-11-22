"""Compatibility exports for the v2 database schema and setup command."""

from crit_app_v2.db.schema import (
    create_access_table,
    create_encounter_table,
    create_party_error_table,
    create_party_report_table,
    create_player_analysis_creation_table,
    create_player_error_table,
    create_report_table,
)
from crit_app_v2.db.setup import initialize_database, main

__all__ = [
    "create_access_table",
    "create_encounter_table",
    "create_party_error_table",
    "create_party_report_table",
    "create_player_analysis_creation_table",
    "create_player_error_table",
    "create_report_table",
    "initialize_database",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
