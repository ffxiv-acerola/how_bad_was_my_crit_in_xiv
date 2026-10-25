"""Domain types and transformations for entered job statistics."""

from crit_app_v2.job_stats.form_validation import validate_job_stats_form
from crit_app_v2.job_stats.models import BuildModel, BuildProvider, JobStatsModel, Role
from crit_app_v2.job_stats.roles import ROLE_SPECS, RoleSpec
from crit_app_v2.job_stats.stats import STAT_INPUTS, Stats

__all__ = [
    "BuildModel",
    "BuildProvider",
    "JobStatsModel",
    "ROLE_SPECS",
    "Role",
    "RoleSpec",
    "ROLE_SPECS",
    "Stats",
    "validate_job_stats_form",
    "STAT_INPUTS",
]
