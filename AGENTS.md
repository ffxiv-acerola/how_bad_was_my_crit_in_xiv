# Development Guide

## Direction

Active application development is in `crit_app_v2`, which uses Dash Mantine
Components (DMC) for its UI. `crit_app` is the legacy application and is kept
separate while the replacement is built.

- Do not add DBC components, Bootstrap-specific callback properties, or
  framework adapter layers to `crit_app_v2`.
- Do not import legacy application pages, cards, callbacks, or UI helpers into
  `crit_app_v2`. Extract framework-independent logic into a v2 domain module
  when it is needed.
- The application root must keep a `dmc.MantineProvider` above
  `dash.page_container` so every page has Mantine context.
- Use DMC-native component APIs. Selects use `data`; input validation uses
  `error`.

## Architecture: Organize by Domain

Code is organized around data types and transformations. Player and party
analysis are workflows that compose shared domain functionality.

Preferred dependency direction:

```text
Dash pages/callbacks -> DMC UI adapters -> domain modules -> persistence/API adapters
```

Domain modules do not import Dash, DMC, DBC, or other presentation code.
Reusable data validation, provider parsing, and calculations belong in domain
modules, not `pages/`, card builders, or callback modules.

Domain packages use focused modules such as:

```text
crit_app_v2/job_stats/
    models.py            # Pydantic models, enums, validation
    roles.py             # Pure role and job metadata
    ranges.py            # Canonical stat-range reference data
    build_providers.py   # Etro/XIVGear parsing and provider rules
    transforms.py        # Domain transformations and calculated values
    persistence.py       # Database row/model mapping
```

UI modules may depend on domain packages, for example
`crit_app_v2/ui/mantine/job_stats.py`, but the domain package must remain usable
by player analysis, party analysis, tests, scripts, and persistence without a
Dash app.

## Pydantic Domain Models

Use Pydantic v2 models at boundaries where raw form, external API, or database
data becomes trusted application data.

- Keep a complete domain model strict: required stats should not become
  optional merely because a Dash form begins blank.
- Validate a complete model at submit/analysis boundaries. UI callbacks may
  report partial-field errors, but they are not the source of truth.
- Use `StrEnum` or equivalent string-valued enums for values shared with Dash,
  JSON, and SQLite.
- Keep cross-field invariants in model validators.
- Keep deterministic reference data out of persisted models unless it is a
  user-entered fact.
- Map Pydantic models to database rows in a persistence/mapper layer rather
  than coupling UI components or SQL directly to models.

### Job-stats domain

The job-stats domain includes:

- `Role`: allowable roles (`Tank`, `Healer`, `Melee`, `Physical Ranged`, and
  `Magical Ranged`).
- `BuildModel`: `build_provider`, `build_id`, and optional `build_index` for
  an XIVGear selection.
- `JobStatsModel`: `role`, entered main stat, determination, speed, critical
  hit, direct hit, weapon damage, optional tenacity, and an optional nested
  `BuildModel`.

`JobStatsModel` intentionally does not contain a job. A concrete job is
selected later from FFLogs and belongs to a job-aware analysis/request model.

Tenacity rules are domain invariants:

- Tanks require Tenacity.
- Non-tanks must not provide Tenacity.

`crit_app_v2.job_stats.ranges.STAT_RANGES` is the canonical source for stat
ranges. UI code and model definitions must derive their limits from it rather
than duplicate constants.

Role metadata must be framework-independent. It may derive labels,
placeholders, speed-stat type, and whether Tenacity is required, but it must
not contain `html.*`, `dbc.*`, or `dmc.*` components. Individual UI adapters
turn the pure metadata into framework-specific labels and tooltips.

## Build Providers and Persistence

Etro and XIVGear parsing should produce typed domain data or typed errors, not
component-specific tuples, feedback elements, hidden flags, or validation
booleans. UI callbacks decide how to render a successful result or error.

The current `report` table stores build provider and build ID. If a selected
XIVGear `build_index` must survive persistence, add an explicit schema
migration and persistence mapping for it; do not silently discard it.

## Dash 4

Use Dash 4 background callbacks, not the removed `dash.long_callback` API:

- use `DiskcacheManager`;
- configure `background_callback_manager` on `dash.Dash`;
- use `@app.callback(..., background=True)` for background work.

## Implementation Practice

- Keep the v2 application package independently runnable. Configure its Dash
  pages folder explicitly and use v2-qualified imports.
- Prefer `dmc.Container` for page width, `dmc.Paper` for semantic sections,
  `dmc.Grid`/`dmc.GridCol` for responsive field layouts, and
  `dmc.Stack`/`dmc.Group` for spacing and local alignment.
- Add focused unit tests for Pydantic validation, provider parsing, domain
  transformations, and persistence mapping before wiring them into pages.
