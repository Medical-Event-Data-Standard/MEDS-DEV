from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from meds_testing_helpers.dataset import MEDSDataset
from omegaconf import OmegaConf

from MEDS_DEV import DATASETS
from MEDS_DEV.datasets import __main__ as dataset_main
from tests.utils import NAME_AND_DIR, run_command


def test_dataset_build_resolves_relative_output_dir(monkeypatch, tmp_path):
    output_dirs = []
    commands = []

    @contextmanager
    def fake_temp_env(cfg, requirements):
        yield tmp_path, {}

    def fake_run_in_env(cmd, output_dir, **kwargs):
        commands.append(cmd)
        output_dirs.append(output_dir)

    monkeypatch.setattr(dataset_main, "temp_env", fake_temp_env)
    monkeypatch.setattr(dataset_main, "run_in_env", fake_run_in_env)
    monkeypatch.setattr(
        dataset_main,
        "DATASETS",
        {"test": {"commands": {"build_full": "build {output_dir}"}, "requirements": ""}},
    )

    relative_output_dir = "relative-output"
    dataset_main.main.__wrapped__(
        OmegaConf.create(
            {
                "dataset": "test",
                "output_dir": relative_output_dir,
                "demo": False,
                "do_overwrite": False,
            }
        )
    )

    resolved_output_dir = Path(relative_output_dir).resolve()
    assert output_dirs == [resolved_output_dir]
    assert commands == [f"build {resolved_output_dir}"]


def test_non_dataset_breaks():
    non_dataset = "_not_supported"
    while non_dataset in DATASETS:
        non_dataset = f"_{non_dataset}"

    with TemporaryDirectory() as root_dir:
        output_dir = Path(root_dir) / "output"
        run_command(
            "meds-dev-dataset",
            test_name="Non-dataset should error",
            hydra_kwargs={
                "dataset": non_dataset,
                "output_dir": str(output_dir.resolve()),
            },
            should_error=True,
            want_err_msg=f"Dataset {non_dataset} not currently configured",
        )


@pytest.mark.integration
def test_datasets_configured(demo_dataset: NAME_AND_DIR):
    dataset_name, demo_dataset_dir = demo_dataset

    # Check validity
    try:
        MEDSDataset(root_dir=demo_dataset_dir)
    except Exception as e:
        raise AssertionError(f"Failed to validate dataset {dataset_name} from {demo_dataset_dir}") from e
