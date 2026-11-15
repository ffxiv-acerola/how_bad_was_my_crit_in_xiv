"""Tests for job reference data and build-provider abbreviations."""

import pytest

from crit_app_v2.game_data import MAIN_STAT_SPEC, ROLE_SPECS
from crit_app_v2.game_data.jobs import JOB_SPECS, Job


@pytest.mark.parametrize(
    ("job", "spec"),
    JOB_SPECS.items(),
    ids=[job.name.lower() for job in JOB_SPECS],
)
def test_job_resolves_provider_abbreviations(job, spec):
    """Resolve each job from its provider abbreviations."""
    assert spec.job is job
    assert Job(spec.etro_name) is job
    assert Job(spec.xivgear_name) is job
    assert spec.fflogs_name == job.value
    assert spec.role in ROLE_SPECS
    assert spec.main_stat in MAIN_STAT_SPEC


def test_job_does_not_resolve_unknown_abbreviation():
    """Reject abbreviations that do not identify a job."""
    with pytest.raises(ValueError):
        Job("UNKNOWN")


def test_icon_glyph_matches_legacy_abbreviations():
    """Icon glyphs match the legacy job-icon font abbreviations."""
    from crit_app.job_data.roles import abbreviated_job_map
    from crit_app_v2.game_data import JOB_SPECS

    for spec in JOB_SPECS.values():
        assert spec.icon_glyph == abbreviated_job_map[spec.fflogs_name]
