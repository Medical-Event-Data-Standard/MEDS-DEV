"""Fast registry and configuration validation tests.

These tests verify that all datasets, tasks, and models load correctly and have valid metadata, without
building any datasets, creating venvs, or running any heavy integration steps.
"""

from MEDS_DEV import DATASETS, MODELS, TASKS


def test_datasets_registry_populated():
    assert len(DATASETS) > 0, "DATASETS registry should contain at least one dataset"


def test_tasks_registry_populated():
    assert len(TASKS) > 0, "TASKS registry should contain at least one task"


def test_models_registry_populated():
    assert len(MODELS) > 0, "MODELS registry should contain at least one model"


def test_all_datasets_have_metadata():
    for name, dataset in DATASETS.items():
        assert "metadata" in dataset, f"Dataset {name} missing metadata"
        assert dataset["metadata"] is not None, f"Dataset {name} has None metadata"
        assert dataset["metadata"].description, f"Dataset {name} missing description"
        assert dataset["metadata"].contacts, f"Dataset {name} missing contacts"


def test_all_datasets_have_commands():
    for name, dataset in DATASETS.items():
        commands = dataset.get("commands")
        assert commands is not None, f"Dataset {name} missing commands"
        assert "build_demo" in commands, f"Dataset {name} missing build_demo command"


def test_all_datasets_have_predicates():
    for name, dataset in DATASETS.items():
        predicates = dataset.get("predicates")
        assert predicates is not None, f"Dataset {name} missing predicates file"
        assert predicates.exists(), f"Dataset {name} predicates file does not exist: {predicates}"


def test_all_tasks_have_criteria():
    for name, task in TASKS.items():
        assert "criteria_fp" in task, f"Task {name} missing criteria_fp"
        criteria = task["criteria_fp"]
        assert criteria.exists(), f"Task {name} criteria file does not exist: {criteria}"


def test_all_tasks_supported_datasets_valid():
    """Every dataset listed in a task's supported_datasets must exist in the DATASETS registry."""
    for name, task in TASKS.items():
        metadata = task.get("metadata")
        if metadata is None or metadata.supported_datasets is None:
            continue
        for dataset in metadata.supported_datasets:
            assert dataset in DATASETS, (
                f"Task {name} references unsupported dataset '{dataset}'. "
                f"Valid datasets: {', '.join(DATASETS.keys())}"
            )


def test_all_models_have_metadata():
    for name, model in MODELS.items():
        assert "metadata" in model, f"Model {name} missing metadata"
        assert model["metadata"] is not None, f"Model {name} has None metadata"
        assert model["metadata"].description, f"Model {name} missing description"


def test_all_models_have_commands():
    for name, model in MODELS.items():
        commands = model.get("commands")
        assert commands is not None, f"Model {name} missing commands"
        has_unsupervised = "unsupervised" in commands
        has_supervised = "supervised" in commands
        assert has_unsupervised or has_supervised, (
            f"Model {name} must have at least one of unsupervised/supervised commands"
        )


def test_all_models_requirements_exist_if_declared():
    """If a model declares a requirements file, verify it exists on disk."""
    for name, model in MODELS.items():
        reqs = model.get("requirements")
        if reqs is not None:
            assert reqs.exists(), f"Model {name} requirements file does not exist: {reqs}"


def test_task_dataset_coverage():
    """At least one task should reference at least one dataset, ensuring the integration test matrix is non-
    empty."""
    datasets_with_tasks = set()
    for task in TASKS.values():
        metadata = task.get("metadata")
        if metadata and metadata.supported_datasets:
            datasets_with_tasks.update(metadata.supported_datasets)

    # This is informational — not all datasets may have tasks yet, so we just check the set is non-empty
    assert len(datasets_with_tasks) > 0, "No tasks reference any datasets — integration test matrix is empty"
