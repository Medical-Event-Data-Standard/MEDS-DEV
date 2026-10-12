# Contributors Guide

Thank you for your interest in contributing to this project. The following sections outline the expectations
for contributors.

## Good Practice

- Discuss large changes with the maintainers before significant work begins.
- Keep commits focused and provide clear commit messages.
- Include tests for new functionality and bug fixes.
- Ensure documentation is updated for user-facing changes.

## Installing the Project for Development

This project uses [`uv`](https://docs.astral.sh/uv/) for environment management. To set up the project for
development, clone the repository, then sync the uv environment and install the pre-commit hook:

```bash
uv sync                   # Creates .venv and installs the project (editable) plus the dev/test extras.
uv run pre-commit install # Installs the Git pre-commit hook so checks run automatically on commit.
```

`uv sync` installs `MEDS-DEV` in editable mode, so source edits take effect without reinstalling.
Prefixing commands with `uv run` (e.g. `uv run pytest`) runs them inside the project environment
without activating it. Activating the environment is optional; if you prefer to drop the `uv run`
prefix, activate it first:

```bash
source .venv/bin/activate # Optional — lets you run `pytest`/`pre-commit` directly, without `uv run`.
```

## Documentation Standards

Documentation should be written using
[Google style docstrings](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html).
API validation can be tested directly inside these docstrings via doctests; this behavior is encouraged.

Helpers like `yaml_disk` and `print_directory` can be made available by
installing the helpers [`yaml_to_disk`](https://github.com/mmcdermott/yaml_to_disk) (which allows you to
populate temporary directories via a yaml snippet) and
[`pretty-print-directory`](https://github.com/mmcdermott/pretty-print-directory) (which allows you to print a
directory structure for doctest prettification) in the development environment. Once installed, these packages
_automatically register in the doctest namespace within pytest_, so you can use them directly in doctests
without needing to import them.

A global `conftest.py` further populates the namespace using `pytest`'s `doctest_namespace` fixture, meaning
you rarely need explicit imports in doctests.

## Running Checks

Pre-commit should run automatically upon commit (if you have installed the hooks above). You can also run it
directly via:

```bash
uv run pre-commit run --all-files
```

You can also run the tests. The suite is split into a fast lane and a full integration lane via the
`integration` pytest marker, and doctests are opt-in through `--doctest-modules` (they are **not**
run by a bare `pytest` invocation).

For quick feedback while developing, run the fast lane — doctests plus unit/registry tests, no
dataset builds or model virtual environments:

```bash
uv run pytest --doctest-modules -m "not integration" -x
```

To run the full suite, including the end-to-end integration tests that build datasets, create model
environments, and run train/predict/evaluate:

```bash
uv run pytest -v -s --doctest-modules
```

Tests and pre-commit checks are run as part of the continuous integration process, so any failures will prevent
pull requests from being merged.
