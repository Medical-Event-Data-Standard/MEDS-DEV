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


# Each case: (label, changed_files, expected-subset-of-classification).
# Only the keys present in `expected` are asserted, so cases stay focused on the decision they probe.
CASES = [
    (
        "docs_only_top_level",
        ["README.md", "CONTRIBUTORS.md", "CLAUDE.md"],
        {
            "run_full": False,
            "docs_only": True,
            "changed_datasets": [],
            "changed_tasks": [],
            "changed_models": [],
        },
    ),
    (
        "docs_only_nested_readme",
        ["src/MEDS_DEV/datasets/MIMIC-IV/README.md"],
        {"run_full": False, "docs_only": True, "changed_datasets": []},
    ),
    (
        "single_dataset",
        ["src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml"],
        {
            "run_full": False,
            "docs_only": False,
            "changed_datasets": ["MIMIC-IV"],
            "changed_tasks": [],
            "changed_models": [],
        },
    ),
    (
        "single_task_keeps_relative_name",
        ["src/MEDS_DEV/tasks/mortality/in_icu/first_24h.yaml"],
        {"run_full": False, "changed_tasks": ["mortality/in_icu/first_24h"], "changed_datasets": []},
    ),
    (
        "single_model",
        ["src/MEDS_DEV/models/random_predictor/model.yaml"],
        {"run_full": False, "changed_models": ["random_predictor"], "changed_datasets": []},
    ),
    (
        "core_file_promotes_to_full",
        ["src/MEDS_DEV/utils.py"],
        {"run_full": True, "docs_only": False},
    ),
    (
        "conftest_promotes_to_full",
        ["tests/conftest.py"],
        {"run_full": True},
    ),
    (
        "workflow_change_promotes_to_full",
        [".github/workflows/tests.yaml"],
        {"run_full": True},
    ),
    (
        "dataset_test_file_promotes_to_full",
        ["tests/test_0_datasets.py"],
        {"run_full": True},
    ),
    (
        "registry_test_stays_fast",
        ["tests/test_registry_validation.py"],
        {
            "run_full": False,
            "docs_only": False,
            "changed_datasets": [],
            "changed_tasks": [],
            "changed_models": [],
        },
    ),
    (
        "unknown_file_promotes_to_full",
        ["some_top_level_thing.py"],
        {"run_full": True},
    ),
    (
        "empty_diff_runs_full",
        [],
        {"run_full": True, "docs_only": False},
    ),
    (
        "docs_plus_code_is_not_docs_only",
        ["README.md", "src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml"],
        {"run_full": False, "docs_only": False, "changed_datasets": ["MIMIC-IV"]},
    ),
    (
        "core_override_wins_over_component",
        ["src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml", "src/MEDS_DEV/utils.py"],
        {"run_full": True},
    ),
    (
        "multiple_datasets_sorted_and_deduped",
        [
            "src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml",
            "src/MEDS_DEV/datasets/MIMIC-IV/predicates.yaml",
            "src/MEDS_DEV/datasets/eICU/dataset.yaml",
        ],
        {"run_full": False, "changed_datasets": ["MIMIC-IV", "eICU"]},
    ),
]


@pytest.mark.parametrize("label,changed_files,expected", CASES, ids=[c[0] for c in CASES])
def test_classify_changes(label, changed_files, expected):
    result = classify_changes(changed_files)
    for key, want in expected.items():
        assert result[key] == want, f"[{label}] key {key!r}: got {result[key]!r}, want {want!r}"


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
