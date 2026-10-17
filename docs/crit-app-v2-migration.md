# V2 Replacement Progress

This document tracks concrete work for the `crit_app_v2` replacement. General
architecture and coding conventions belong in [`AGENTS.md`](../AGENTS.md).

## Runtime layout

- `crit_app` remains the legacy application.
- `crit_app_v2` is the independently runnable DMC application under active
  development.
- Both use the repository's Dash 4.4 environment, but they must run as
  separate processes; do not import both Dash apps into the same process.
- The v2 entry point is `crit_app_v2.app`. It explicitly discovers pages from
  `crit_app_v2/pages`.
- The initial v2 player-analysis workbench is registered at `/analysis`.

## Completed

- [x] Added `dash-mantine-components` and upgraded the shared environment to
  Dash 4.4.
- [x] Updated the legacy application's long callback to Dash 4 background
  callback APIs.
- [x] Created an independent DMC-only `crit_app_v2` root layout with
  `dmc.MantineProvider`.
- [x] Removed DBC and legacy application imports from `crit_app_v2`.
- [x] Added `crit_app_v2` to the wheel build package list.
- [x] Added a `/analysis` workbench page that renders the job-stats form.
- [x] Created the framework-independent `crit_app_v2.job_stats` domain:
  - `Role` and `BuildProvider` string enums;
  - strict `BuildModel` and `JobStatsModel` Pydantic models;
  - Tank/Tenacity and provider/build-index invariants;
  - pure `ROLE_SPECS` metadata;
  - canonical `STAT_RANGES` reference data.
- [x] Made the Mantine job-stats form use the v2 role metadata and stat ranges.
- [x] Added focused job-stats model tests.

## Current limitations

- The v2 shell deliberately has no header, navigation, global history stores,
  saved-gearset stores, or legacy modal callbacks.
- The job-stats form is presentational. It does not yet have role-change,
  validation, build-provider, saved-gearset, FFLogs, analysis, or persistence
  callbacks.
- `build_index` exists in `BuildModel` but the legacy `report` table has no
  dedicated persisted column for it.
- V2 has no background callback or disk cache yet. Add a v2-specific cache
  path when background analysis is introduced.

## Verification baseline

Last verified after the v2 package split:

```text
pytest -q crit_app_v2/tests/test_job_stats_models.py  # 14 passed
ruff check crit_app_v2                              # passed
ruff format --check crit_app_v2                     # passed
```

The v2 app imports successfully and registers `/analysis`.

## Next work

1. Add a job-stats form adapter that collects DMC values and constructs a
   complete `JobStatsModel` at the submit boundary.
2. Add DMC callbacks for role-dependent labels, speed-stat labels, Tenacity
   visibility, and field-level `error` rendering from Pydantic validation.
3. Implement `job_stats/build_providers.py` so Etro and XIVGear parsing return
   typed data or typed errors rather than UI-specific tuples.
4. Add job-stats persistence mapping and an explicit database migration if
   `build_index` must persist.
5. Add the encounter/FFLogs domain and compose it with job stats in a
   player-analysis request model.
6. Add analysis execution and a v2-specific Dash background callback manager.
7. Build party analysis by composing shared encounter and job-stats domains,
   rather than duplicating player-analysis forms or validation.

## Operational notes

- Run the v2 app as a module so package imports resolve consistently:

  ```bash
  uv run python -m crit_app_v2.app
  ```

- The legacy and v2 apps both default to Dash's standard port. Run only one at
  a time until the v2 entry point receives its own configured development port.
