"""Table-driven unit tests for the CI scope-selection logic.

``.github/scripts/select_test_scope.py`` decides which CI test lanes run for a given diff. It gates
the entire test workflow, so its `classify_changes` routine is worth exercising directly (it is not
importable as a normal package, so we load it from its path).
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "select_test_scope.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("select_test_scope", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select_test_scope = _load_module()
classify_changes = select_test_scope.classify_changes


# Each case contains the complete set of fields that control workflow execution. ``reason`` is
# intentionally checked separately because it is diagnostic text, not an input to lane selection.
def expected_scope(*, run_full=False, docs_only=False, datasets=(), tasks=(), models=()):
    return {
        "run_full": run_full,
        "docs_only": docs_only,
        "changed_datasets": list(datasets),
        "changed_tasks": list(tasks),
        "changed_models": list(models),
    }


CASES = [
    (
        "docs_only_top_level",
        ["README.md", "CONTRIBUTORS.md", "CLAUDE.md"],
        expected_scope(docs_only=True),
    ),
    (
        "docs_only_nested_readme",
        ["src/MEDS_DEV/datasets/MIMIC-IV/README.md"],
        expected_scope(docs_only=True),
    ),
    (
        "single_dataset",
        ["src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml"],
        expected_scope(datasets=("MIMIC-IV",)),
    ),
    (
        "single_task_keeps_relative_name",
        ["src/MEDS_DEV/tasks/mortality/in_icu/first_24h.yaml"],
        expected_scope(tasks=("mortality/in_icu/first_24h",)),
    ),
    (
        "single_model",
        ["src/MEDS_DEV/models/random_predictor/model.yaml"],
        expected_scope(models=("random_predictor",)),
    ),
    (
        "core_file_promotes_to_full",
        ["src/MEDS_DEV/utils.py"],
        expected_scope(run_full=True),
    ),
    (
        "conftest_promotes_to_full",
        ["tests/conftest.py"],
        expected_scope(run_full=True),
    ),
    (
        "workflow_change_promotes_to_full",
        [".github/workflows/tests.yaml"],
        expected_scope(run_full=True),
    ),
    (
        "dataset_test_file_promotes_to_full",
        ["tests/test_0_datasets.py"],
        expected_scope(run_full=True),
    ),
    (
        "registry_test_stays_fast",
        ["tests/test_registry_validation.py"],
        expected_scope(),
    ),
    (
        "unknown_file_promotes_to_full",
        ["some_top_level_thing.py"],
        expected_scope(run_full=True),
    ),
    (
        "empty_diff_runs_full",
        [],
        expected_scope(run_full=True),
    ),
    (
        "docs_plus_code_is_not_docs_only",
        ["README.md", "src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml"],
        expected_scope(datasets=("MIMIC-IV",)),
    ),
    (
        "core_override_wins_over_component",
        ["src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml", "src/MEDS_DEV/utils.py"],
        expected_scope(run_full=True, datasets=("MIMIC-IV",)),
    ),
    (
        "multiple_datasets_sorted_and_deduped",
        [
            "src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml",
            "src/MEDS_DEV/datasets/MIMIC-IV/predicates.yaml",
            "src/MEDS_DEV/datasets/eICU/dataset.yaml",
        ],
        expected_scope(datasets=("MIMIC-IV", "eICU")),
    ),
]


@pytest.mark.parametrize("label,changed_files,expected", CASES, ids=[c[0] for c in CASES])
def test_classify_changes(label, changed_files, expected):
    result = classify_changes(changed_files)
    actual = {key: value for key, value in result.items() if key != "reason"}
    assert actual == expected, f"[{label}] got {actual!r}, want {expected!r}"
    assert isinstance(result["reason"], str) and result["reason"]


def test_classify_changes_returns_all_keys():
    result = classify_changes(["README.md"])
    assert set(result) == {
        "run_full",
        "docs_only",
        "changed_datasets",
        "changed_tasks",
        "changed_models",
        "reason",
    }
