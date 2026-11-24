"""Tests for public game-data and build-provider package imports."""

import importlib

import pytest

from crit_app_v2.build_providers.models.etro_models import EtroTotalParam
from crit_app_v2.build_providers.models.xivgear_models import LoadedXivGearSet


@pytest.mark.parametrize(
    ("package_name", "source_name", "names"),
    [
        (
            "crit_app_v2.game_data",
            "crit_app_v2.game_data.jobs",
            ("Job", "JobSpec", "JOB_SPECS"),
        ),
        (
            "crit_app_v2.game_data",
            "crit_app_v2.game_data.roles",
            ("Role", "RoleSpec", "ROLE_SPECS"),
        ),
        (
            "crit_app_v2.game_data",
            "crit_app_v2.game_data.stats",
            (
                "Stats",
                "MainStats",
                "SpeedStats",
                "StatInput",
                "MainStatSpec",
                "SpeedStatSpec",
                "STAT_INPUTS",
                "MAIN_STAT_SPEC",
                "SPEED_STAT_SPEC",
            ),
        ),
        (
            "crit_app_v2.build_providers.models",
            "crit_app_v2.build_providers.models.models",
            (
                "BuildProvider",
                "BuildUrl",
                "InternalBuild",
                "RoleBuildStatsModel",
                "ValidatedRoleBuild",
            ),
        ),
        (
            "crit_app_v2.build_providers.models",
            "crit_app_v2.build_providers.models.etro_models",
            ("EtroBuildResponse", "LoadedEtroBuild"),
        ),
        (
            "crit_app_v2.build_providers.models",
            "crit_app_v2.build_providers.models.xivgear_models",
            ("LoadedXivGearBuild",),
        ),
        (
            "crit_app_v2.build_providers",
            "crit_app_v2.build_providers.models",
            (
                "BuildProvider",
                "BuildUrl",
                "EtroBuildResponse",
                "InternalBuild",
                "LoadedEtroBuild",
                "LoadedXivGearBuild",
                "RoleBuildStatsModel",
                "ValidatedRoleBuild",
            ),
        ),
        (
            "crit_app_v2.build_providers",
            "crit_app_v2.build_providers.errors",
            ("BuildErrorCategory", "BuildProviderError"),
        ),
        (
            "crit_app_v2.build_providers",
            "crit_app_v2.build_providers.form_validation",
            (
                "FormStatValue",
                "JobStatsFormValidation",
                "StatValidation",
                "validate_job_stats_form",
            ),
        ),
        (
            "crit_app_v2.analysis",
            "crit_app_v2.analysis.models",
            ("PlayerAnalysisStats", "PreparedPlayerAnalysis"),
        ),
        (
            "crit_app_v2.analysis",
            "crit_app_v2.analysis.player_analysis",
            (
                "DISCRETIZATION_LEVEL_MAP",
                "compute_party_bonus",
                "correct_final_phase",
            ),
        ),
        (
            "crit_app_v2.gearsets",
            "crit_app_v2.gearsets.models",
            (
                "MAX_GEARSET_NAME_LENGTH",
                "MAX_SAVED_GEARSETS",
                "GearsetLibrary",
                "SavedGearset",
            ),
        ),
        (
            "crit_app_v2.gearsets",
            "crit_app_v2.gearsets.errors",
            ("GearsetLibraryError", "GearsetLimitError", "GearsetNotFoundError"),
        ),
        (
            "crit_app_v2.gearsets",
            "crit_app_v2.gearsets.legacy",
            ("LegacyMigrationResult", "migrate_legacy_gearsets"),
        ),
        (
            "crit_app_v2.gearsets",
            "crit_app_v2.gearsets.storage",
            ("library_from_storage", "library_to_storage"),
        ),
    ],
    ids=[
        "game-data-jobs",
        "game-data-roles",
        "game-data-stats",
        "provider-models",
        "etro-models",
        "xivgear-models",
        "provider-package",
        "provider-errors",
        "form-validation",
        "analysis-models",
        "analysis-functions",
        "gearset-models",
        "gearset-errors",
        "gearset-legacy",
        "gearset-storage",
    ],
)
def test_public_package_exports_reference_original_objects(package_name, source_name, names):
    """Export each public object without introducing a second definition."""
    package = importlib.import_module(package_name)
    source = importlib.import_module(source_name)

    for name in names:
        assert name in package.__all__
        assert getattr(package, name) is getattr(source, name)


@pytest.mark.parametrize(
    "package_name",
    ["crit_app_v2.build_providers", "crit_app_v2.build_providers.models"],
    ids=["provider-package", "models-package"],
)
def test_internal_models_are_not_public_exports(package_name):
    """Keep internal models available from their modules, not package exports."""
    package = importlib.import_module(package_name)

    for model in (EtroTotalParam, LoadedXivGearSet):
        assert model.__name__ not in package.__all__
        assert not hasattr(package, model.__name__)
