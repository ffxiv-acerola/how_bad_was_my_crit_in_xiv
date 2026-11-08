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
Dash pages/callbacks -> DMC UI components -> domain modules
                                               -> persistence/API adapters
```

Domain modules do not import Dash, DMC, DBC, or other presentation code.
Reusable data validation, provider transformations, and calculations belong in
domain modules, not `pages/`, card builders, or callback modules. Provider
modules may depend on external API clients to fetch data, then normalize it into
framework-independent models.

The active v2 package is organized by domain and responsibility:

```text
crit_app_v2/
    game_data/
        jobs.py           # Job enum and job reference metadata
        roles.py          # Role enum and role metadata
        stats.py          # Stat enums, metadata, and canonical ranges
    build_providers/
        models/
            models.py         # Shared provider, URL, stats, and internal-build models
            etro_models.py    # Etro response and loaded-build models
            xivgear_models.py # Loaded XIVGear sheet and set models
        etro.py              # Etro API access and response transformation
        xivgear.py           # XIVGear API access and response transformation
        form_validation.py # Incomplete job-stat form validation
    ui/                   # DMC components and presentation adapters
    pages/                # Dash pages and callbacks
```

`game_data` and provider models should remain framework-independent and usable
by pages, tests, scripts, and persistence without a Dash app. UI modules may
depend on these domain packages, but domain code must not depend on UI modules.

## Pydantic Domain Models

Use Pydantic v2 models at boundaries where raw form, external API, or database
data becomes trusted application data.

- Keep a complete domain model strict: required stats should not become
  optional merely because a Dash form begins blank.
- Validate a complete model at submit/analysis boundaries. Re-validate raw
  submission data as a strict domain model immediately before analysis,
  persistence, or another trusted-domain workflow.
- Keep incomplete form state separate from complete domain models. When live
  field feedback is needed, use a framework-independent draft validator with a
  typed result; callbacks render those results but do not define or duplicate
  validation rules.
- Use `StrEnum` or equivalent string-valued enums for values shared with Dash,
  JSON, and SQLite.
- Keep cross-field invariants in model validators.
- Keep deterministic reference data out of persisted models unless it is a
  user-entered fact.
- Map Pydantic models to database rows in a persistence/mapper layer rather
  than coupling UI components or SQL directly to models.

### Job and build models

Reference data lives in `crit_app_v2.game_data`. Use enum keys to represent
relationships between specs, then resolve those keys explicitly through the
corresponding registry where needed. For example, `JobSpec.role` refers to a
`Role`, `JobSpec.main_stat` refers to a `MainStats`, and `RoleSpec.speed_stat`
refers to a `SpeedStats` entry. Avoid embedding another spec object in a spec.

`crit_app_v2.game_data.stats.STAT_INPUTS` is the canonical source for stat
ranges. UI code, draft validation, and model definitions must derive their
limits from it rather than duplicate constants.

The public provider models are exported from
`crit_app_v2.build_providers.models` and `crit_app_v2.build_providers`. These
include `BuildUrl`, `RoleBuildStatsModel`, `InternalBuild`, `LoadedEtroBuild`,
and `LoadedXivGearBuild`. `BuildUrl` validates a supported provider URL and
classifies its provider.

Loaded provider-build outputs are role-level: a job may be used internally to
select provider stat fields, but do not expose it as the loaded build's output.
For XIVGear, preserve the original URL and response-relative selected index;
loaded set records preserve their indexes in the API response.

Etro responses are validated with `EtroBuildResponse` at the provider boundary.
The model validates fields used for processing and the required job/role stats
while ignoring unrelated response fields and parameters. XIVGear processing
currently transforms the raw API mapping; a typed response model and response
validation have not yet been added. Do not assume the provider responses have
equivalent validation coverage.

### Draft form validation

A browser form may be incomplete while it is being edited; do not weaken a
complete Pydantic model to represent that temporary state. Draft validation may
accept transient input values such as `None` for an untouched field and `""`
for a field the user cleared. Return field-oriented errors keyed by domain
enums (for example, `Stats`) so UI adapters can map feedback to components
without duplicating validation rules.

Dash callbacks should gather component values into an explicit mapping keyed by
the relevant domain enum, call the draft validator, and map its result to DMC
properties such as `InputWrapper.error`. Keep callback argument order and
positional output wiring in the UI adapter; do not make domain validation rely
on argument order or dictionary iteration order.

UI adapters may hide fields that do not apply to the selected role. Draft
validation should ignore stale values for hidden, non-applicable fields, and
submission adapters should omit those values so strict domain validation sees
only role-valid stats. A successful draft result does not replace strict model
validation at the trusted-workflow boundary.

Tenacity rules are domain invariants:

- Tanks require Tenacity.
- Non-tanks must not provide Tenacity.

Role and stat metadata must be framework-independent and must not contain
`html.*`, `dbc.*`, or `dmc.*` components. UI adapters resolve metadata and turn
it into framework-specific labels, tooltips, and controls.

## Build Providers and Persistence

Etro and XIVGear parsing should produce typed domain data or typed errors, not
component-specific tuples, feedback elements, hidden flags, or validation
booleans. UI callbacks decide how to render a successful result or error.

The legacy `report` table stores build provider and build ID. If a selected
XIVGear `build_index` must survive persistence, add an explicit schema
migration and persistence mapping for it; do not silently discard it.

## Implementation Practice

- Add a concise module docstring at the top of every Python module in
  `crit_app_v2/`. Document classes and functions, including private helpers,
  with short descriptions of their purpose. Provider and domain APIs should
  generally use numpydoc sections for meaningful parameters, return values, and
  exceptions; dataclasses may use numpydoc or a clear general description. Dash
  pages, callbacks, and UI components may use concise general descriptions.
- Keep docstrings aligned with implemented behavior, signatures, return values,
  and propagated or normalized exceptions. Mark empty modules and unfinished
  functions as placeholders rather than describing intended functionality as
  implemented.
- Keep the v2 application package independently runnable. Configure its Dash
  pages folder explicitly and use v2-qualified imports.
- Prefer `dmc.Container` for page width, `dmc.Paper` for semantic sections,
  `dmc.Grid`/`dmc.GridCol` for responsive field layouts, and
  `dmc.Stack`/`dmc.Group` for spacing and local alignment.
- Add focused unit tests for strict-model validation, draft form validation,
  provider parsing, reference-data completeness, domain transformations, and
  persistence mapping before wiring them into pages.
- Give every test function a short docstring describing the behavior or case it
  covers. Add explicit, brief, human-readable `ids` to every parameterized test
  case so test output identifies the scenario; for stacked parametrization,
  provide IDs for each parameter dimension.
- Parameterize stat-boundary tests from canonical `STAT_INPUTS`; do not repeat
  stat ranges in test cases.
- Store tests under `tests/`, mirroring the source code's directory structure.
  For example, tests for `crit_app_v2/build_providers/models/etro_models.py`
  belong under `tests/crit_app_v2/build_providers/models/`. Do not add test
  modules inside application packages.

### Code Quality Checks

Install the development tools with `uv sync --group dev`. For changed v2 code,
run the relevant checks before considering the work complete:

```bash
uv run ruff check <changed paths>
uv run ruff check --select I <changed paths>
uv run ruff format --check <changed paths>
uv run basedpyright <changed Python modules>
uv run pytest -q <relevant test paths>
```

`pre-commit` also runs linting, import sorting, formatting,
docstring formatting, and basic file checks; run it on changed files with
`uv run pre-commit run --files <changed paths>`.

The current package-wide BasedPyright check reports existing errors. Check
changed modules and do not introduce new type errors; do not silence
diagnostics or weaken checks just to make a run pass. DMC currently has no type stubs, so its missing-stub warning may remain.
