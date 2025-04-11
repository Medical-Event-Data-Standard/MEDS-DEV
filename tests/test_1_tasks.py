import tempfile
from pathlib import Path

import pytest

from MEDS_DEV import DATASETS, TASKS
from tests.utils import NAME_AND_DIR, run_command


@pytest.mark.parametrize("task", TASKS)
def test_non_task_non_dataset_breaks(task: str):
    non_dataset = "_not_supported"
    while non_dataset in DATASETS:
        non_dataset = f"_{non_dataset}"

    with tempfile.TemporaryDirectory() as tmpdir:
        labels_dir = Path(tmpdir) / "task_labels"
        run_command(
            "meds-dev-task",
            test_name="Non-dataset should error",
            hydra_kwargs={
                "task": task,
                "dataset": non_dataset,
                "dataset_dir": tmpdir,
                "output_dir": str(labels_dir),
            },
            should_error=True,
            want_err_msg=f"Dataset {non_dataset} not currently configured",
        )


def test_non_task_breaks(demo_dataset: NAME_AND_DIR):
    (dataset_name, dataset_dir) = demo_dataset

    non_task = "_not_supported"
    while non_task in TASKS:
        non_task = f"_{non_task}"

    task_labels_dir = dataset_dir / "task_labels"

    run_command(
        "meds-dev-task",
        test_name="Non-task should error",
        hydra_kwargs={
            "task": non_task,
            "dataset": dataset_name,
            "dataset_dir": str(dataset_dir.resolve()),
            "output_dir": str(task_labels_dir.resolve()),
        },
        should_error=True,
        want_err_msg=f"Task {non_task} not currently configured",
    )


def test_tasks_configured(demo_dataset: NAME_AND_DIR, task_labels: NAME_AND_DIR):
    dataset_name, dataset_dir = demo_dataset
    task_name, task_labels_dir = task_labels

    files = list(task_labels_dir.glob("**/*.parquet"))
    assert files, f"No files found for task {task_name} in dataset {dataset_name}"


def test_task_consistent_when_using_manual_predicates(demo_dataset: NAME_AND_DIR, task_labels: NAME_AND_DIR):
    dataset_name, dataset_dir = demo_dataset
    task_name, task_labels_dir = task_labels

    dataset_predicates_path = DATASETS[dataset_name]["predicates"]

    with tempfile.TemporaryDirectory() as tmpdir:
        alt_task_labels_dir = Path(tmpdir) / "task_labels"
        run_command(
            "meds-dev-task",
            test_name=f"Task {task_name} should run for {dataset_name} with manual predicates",
            hydra_kwargs={
                "task": task_name,
                "dataset": dataset_name,
                "dataset_dir": str(dataset_dir.resolve()),
                "output_dir": str(alt_task_labels_dir.resolve()),
                "dataset_predicates_path": str(dataset_predicates_path),
            },
        )

        for file in alt_task_labels_dir.glob("**/*.parquet"):
            relative_file = file.relative_to(alt_task_labels_dir)
            original_file = task_labels_dir / relative_file
            assert original_file.exists(), f"File {relative_file} not found in original task labels dir"
            assert file.read_bytes() == original_file.read_bytes(), (
                f"File {relative_file} differs from original"
            )
