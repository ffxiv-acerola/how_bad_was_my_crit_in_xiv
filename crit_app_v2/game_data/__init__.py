"""Framework-independent job, role, and stat reference data."""

from .jobs import JOB_SPECS, Job, JobSpec
from .roles import ROLE_SPECS, Role, RoleSpec
from .stats import (
    MAIN_STAT_SPEC,
    SPEED_STAT_SPEC,
    STAT_INPUTS,
    MainStats,
    MainStatSpec,
    SpeedStats,
    SpeedStatSpec,
    StatInput,
    Stats,
)

__all__ = [
    "JOB_SPECS",
    "MAIN_STAT_SPEC",
    "ROLE_SPECS",
    "SPEED_STAT_SPEC",
    "STAT_INPUTS",
    "Job",
    "JobSpec",
    "MainStatSpec",
    "MainStats",
    "Role",
    "RoleSpec",
    "SpeedStatSpec",
    "SpeedStats",
    "StatInput",
    "Stats",
]
