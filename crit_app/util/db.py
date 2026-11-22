"""Compatibility exports for database functions moved to ``crit_app_v2.db``."""

from crit_app_v2.db.access import update_access_table
from crit_app_v2.db.encounter import (
    compute_party_bonus,
    get_party_analysis_calculation_info,
    get_player_analysis_job_records,
    read_player_analysis_info,
    update_encounter_table,
)
from crit_app_v2.db.errors import (
    insert_error_party_analysis,
    insert_error_player_analysis,
)
from crit_app_v2.db.party_analysis import (
    check_prior_party_analysis_via_player_analyses,
    check_valid_party_analysis_id,
    get_party_analysis_encounter_info,
    get_party_analysis_player_build,
    unflag_party_report_recompute,
    update_party_report_table,
)
from crit_app_v2.db.player_analysis import (
    check_valid_player_analysis_id,
    player_analysis_meta_info,
    retrieve_player_analysis_information,
    search_prior_player_analyses,
    unflag_redo_rotation,
    unflag_report_recompute,
    update_player_analysis_creation_table,
    update_report_table,
)

__all__ = [
    "check_prior_party_analysis_via_player_analyses",
    "check_valid_party_analysis_id",
    "check_valid_player_analysis_id",
    "compute_party_bonus",
    "get_party_analysis_calculation_info",
    "get_party_analysis_encounter_info",
    "get_party_analysis_player_build",
    "get_player_analysis_job_records",
    "insert_error_party_analysis",
    "insert_error_player_analysis",
    "player_analysis_meta_info",
    "read_player_analysis_info",
    "retrieve_player_analysis_information",
    "search_prior_player_analyses",
    "unflag_party_report_recompute",
    "unflag_redo_rotation",
    "unflag_report_recompute",
    "update_access_table",
    "update_encounter_table",
    "update_party_report_table",
    "update_player_analysis_creation_table",
    "update_report_table",
]
