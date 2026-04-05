# CLAUDE.md — MEDS-DEV

## What This Repo Is

MEDS-DEV (Medical Event Data Standard — Decentralized Extensible Validation) is a **benchmark
orchestration system**, not a model training framework. It stores YAML configuration files, task
definitions, training recipes, evaluation pipelines, and results — not runnable ML model code.
Models, datasets, and evaluation tools live in external packages; MEDS-DEV wraps them via CLI
entry points that create virtual environments, run commands, and collect outputs.

The core abstractions are:

- **Datasets** (`src/MEDS_DEV/datasets/`): Each has a `dataset.yaml` (ETL commands),
    `predicates.yaml` (ACES predicates), and `requirements.txt`.
- **Tasks** (`src/MEDS_DEV/tasks/`): ACES task configuration YAML files defining cohort
    extraction criteria. Tasks reference predicates that are overridden per-dataset.
- **Models** (`src/MEDS_DEV/models/`): Each has a `model.yaml` (train/predict shell commands
    with template variables), `requirements.txt`, and optional Python scripts.
- **Results** (`src/MEDS_DEV/results/`): JSON result packaging and validation.

## Build & Install

```bash
# Standard install (users reproducing benchmarks)
pip install MEDS-DEV

# Development install (contributors)
pip install -e ".[dev,tests]"
```

Requires Python ≥ 3.11. Uses `setuptools-scm` for versioning (version is derived from git tags).

## Running Tests

Tests are split into two tiers using pytest markers:

- **Fast tests** (`-m "not integration"`): doctests, registry validation, unit tests, CLI error
    tests. No venvs, no dataset builds. Target: under 5 minutes.
- **Integration tests** (`-m integration`): end-to-end tests that build datasets, extract tasks,
    create model venvs, train/predict, evaluate, and package results.

```bash
# Fast checks only (doctests + unit + registry validation)
pytest --doctest-modules -m "not integration" -x

# Full integration suite (builds demo datasets, creates model venvs, runs end-to-end)
pytest -v -s -x --doctest-modules

# One dataset lane (integration tests scoped to a single dataset)
pytest -v -s -x -m integration --test_dataset=MIMIC-IV_DEMO

# One task lane
pytest -v -s -x -m integration --test_task=mortality/in_icu/first_24h

# One model lane
pytest -v -s -x -m integration --test_model=random_predictor

# Full suite with persistent caching (much faster on repeat local runs)
mkdir -p /tmp/meds_dev_cache
pytest -v -s -x --doctest-modules \
    --persistent_cache_dir=/tmp/meds_dev_cache \
    --cache_dataset=all --cache_task=all --cache_model=all \
    --reuse_cached_dataset=all
```

**Key test options:**

- `--persistent_cache_dir=DIR` — persist built datasets/models across runs (DIR must exist)
- `--cache_dataset=NAME|all` — cache dataset builds in persistent dir
- `--cache_task=NAME|all` — cache task extractions
- `--cache_model=NAME|all` — cache model outputs
- `--reuse_cached_dataset=NAME|all` — skip re-running dataset builds if cached
- `--test_dataset=NAME|all`, `--test_task=NAME|all`, `--test_model=NAME|all` — filter which
    components to test

Tests are **ordered** by `pytest_collection_modifyitems` in conftest.py to ensure datasets are
built before tasks, and tasks before models. Tests within a model are grouped so venvs can be
cleaned up between models.

### CI Tiers

CI uses a tiered, change-aware strategy (see `.github/workflows/tests.yaml`):

1. **Fast checks** — always run (lint + doctests + unit/registry tests)
2. **Affected integration lanes** — run only for changed datasets, tasks, or models
3. **Full integration** — runs on push to `main`, weekly schedule, `full-ci` PR label, or
    when shared/core files change

To force a full CI run on a PR, add the `full-ci` label.

## Code Quality

```bash
# Pre-commit runs the configured linters/formatters
pre-commit run --all-files
```

## Architecture

### Entry Points (CLI commands)

Defined in `pyproject.toml` under `[project.scripts]`:

- `meds-dev-dataset` → `MEDS_DEV.datasets.__main__:main`
- `meds-dev-task` → `MEDS_DEV.tasks.__main__:main`
- `meds-dev-model` → `MEDS_DEV.models.__main__:main`
- `meds-dev-evaluation` → `MEDS_DEV.evaluation.__main__:main`
- `meds-dev-pack-result` → `MEDS_DEV.results.__main__:pack_result`
- `meds-dev-validate-result` → `MEDS_DEV.results.__main__:validate_result`

All entry points use **Hydra** for configuration. Configs live in `src/MEDS_DEV/configs/` as
YAML files prefixed with `_`. Arguments are passed as Hydra overrides (dot-list syntax).

### Virtual Environment Isolation

Models and datasets run in isolated venvs to avoid dependency conflicts. The venv lifecycle is
managed by `src/MEDS_DEV/utils.py`:

- `install_venv(venv_dir, requirements)` — creates venv + pip installs requirements
- `temp_env(cfg, requirements)` — context manager that sets up venv + PATH
- `run_in_env(cmd, output_dir, env)` — runs a shell command in the venv, writes a `.done`
    sentinel on success to support idempotent reruns

### Registry Dictionaries

On import, `MEDS_DEV.__init__` populates three module-level dicts by scanning package resources:

- `DATASETS` — keyed by slash-separated path from `datasets/` dir (e.g., `"MIMIC-IV"`)
- `TASKS` — keyed by slash-separated path from `tasks/` dir (e.g., `"mortality/in_icu/first_24h"`)
- `MODELS` — keyed by slash-separated path from `models/` dir (e.g., `"meds_tab/tiny"`)

These are populated at import time via `importlib.resources.files()` + `rglob()`.

### Test Fixtures (tests/conftest.py)

The test suite uses **session-scoped parametrized fixtures** that chain together:

```
demo_dataset (builds MEDS data via meds-dev-dataset)
    → task_labels (extracts labels via meds-dev-task)
        → unsupervised_model (optional pretrain via meds-dev-model)
            → supervised_model (train + predict via meds-dev-model)
                → evaluated_model (evaluate via meds-dev-evaluation)
                    → packaged_result (pack via meds-dev-pack-result)
```

`pytest_generate_tests` dynamically parametrizes based on which tasks support which datasets
(via the `supported_datasets` field in task metadata). The cross-product of datasets × tasks ×
models is filtered by compatibility.

## Conventions

### Code Style

- Python 3.11+ features are expected (match statements, type unions with `|`, etc.)
- Type hints on all function signatures
- Google-style docstrings with `>>>` doctests for all public functions
- Doctests are run as part of the test suite (`--doctest-modules` in pytest config)
- Use `polars` (not pandas) for DataFrame operations
- Use `Path` objects (not strings) for filesystem paths
- Use `OmegaConf` for YAML config loading, `DictConfig` for typed config access

### Adding a New Dataset

1. Create `src/MEDS_DEV/datasets/<name>/` with: `dataset.yaml`, `predicates.yaml`,
    `requirements.txt`, `README.md`
2. `dataset.yaml` must have `metadata` (with `description`, `contacts`, `access_policy`) and
    `commands` (with `build_full` and `build_demo` using `{temp_dir}` and `{output_dir}` placeholders)
3. `predicates.yaml` contains ACES-syntax predicates for task extraction
4. Access policy must be one of: `public_with_approval`, `public_unrestricted`, `institutional`,
    `private_single_use`, `other`

### Adding a New Task

1. Create a YAML file under `src/MEDS_DEV/tasks/<category>/<subcategory>/<name>.yaml`
2. Must be a valid ACES configuration file with predicates left as `???` placeholders
3. Include `metadata.supported_datasets` listing compatible dataset names
4. Add README.md files in parent directories describing the task category

### Adding a New Model

1. Create `src/MEDS_DEV/models/<name>/` with: `model.yaml`, `requirements.txt`, `README.md`
2. `model.yaml` must have `metadata` and `commands` with nested `unsupervised`/`supervised` →
    `train`/`predict` structure
3. Commands use template variables: `{dataset_dir}`, `{labels_dir}`, `{output_dir}`,
    `{model_dir}`, `{model_initialization_dir}`, `{split}`, `{demo}`
4. Predictions must output parquet files compatible with `meds-evaluation`

### YAML Config Conventions

- Task configs: predicates that vary per-dataset use `???` (Hydra missing marker)
- Dataset predicates: use `code: { regex: "^PATTERN//.*" }` syntax
- Model commands: use `|-` for multi-line shell scripts, `>-` for single commands

## Key Dependencies

| Package                  | Purpose                                |
| ------------------------ | -------------------------------------- |
| `meds==0.3.3`            | MEDS data schema and split constants   |
| `es-aces==0.6.1`         | ACES task extraction engine            |
| `hydra-core`             | CLI configuration management           |
| `meds-evaluation==0.0.3` | Prediction evaluation (AUROC, etc.)    |
| `validators`             | Email/URL validation for metadata      |
| `polars`                 | DataFrame operations in tests          |
| `omegaconf`              | YAML config loading (comes with hydra) |

## Common Pitfalls

- **Don't run `pytest` without flags if you just want fast feedback.** The full suite builds
    datasets and model venvs. Use `--doctest-modules -m "not integration"` for quick iteration.
- **Model venvs can conflict with the host environment.** Models run in isolated venvs created
    by `utils.install_venv()`. Don't install model requirements into your dev environment.
- **Task `supported_datasets` is validated against the `DATASETS` registry at import time.**
    If you add a task referencing a dataset that doesn't exist yet, import will fail.
- **The `.done` sentinel file in `run_in_env` means commands are idempotent.** If a command
    succeeded before, it won't re-run. Delete the `.done` file (or pass `do_overwrite=True`) to
    force a re-run.
- **`pytest_collection_modifyitems` reorders tests.** Test file numbering (test_0, test_1, etc.)
    is a hint, but the actual execution order is determined by the sort key in conftest.py.
- **Hydra changes the working directory by default.** Entry points using `@hydra.main` will
    `cd` into a Hydra output directory. Use absolute paths in test fixtures.
