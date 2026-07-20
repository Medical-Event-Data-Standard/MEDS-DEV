from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest
from meds_testing_helpers.dataset import MEDSDataset
from omegaconf import OmegaConf

from MEDS_DEV import DATASETS
from MEDS_DEV.datasets import __main__ as datasets_main
from tests.utils import NAME_AND_DIR, run_command


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


def test_select_build_command():
    commands = {"build_full": "full-cmd", "build_demo": "demo-cmd"}

    assert datasets_main._select_build_command("D", commands, demo=False) == "full-cmd"
    assert datasets_main._select_build_command("D", commands, demo=True) == "demo-cmd"

    with pytest.raises(ValueError, match="does not declare a build_demo command"):
        datasets_main._select_build_command("D", {"build_full": "full-cmd"}, demo=True)


def test_main_selects_build_command(monkeypatch, tmp_path):
    output_dir = tmp_path / "output"
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    run_in_env = Mock()

    @contextmanager
    def fake_temp_env(cfg, requirements):
        yield build_dir, "env"

    monkeypatch.setattr(
        datasets_main,
        "DATASETS",
        {"D": {"commands": {"build_full": "build {output_dir}"}, "requirements": []}},
    )
    monkeypatch.setattr(datasets_main, "temp_env", fake_temp_env)
    monkeypatch.setattr(datasets_main, "run_in_env", run_in_env)

    cfg = OmegaConf.create(
        {"dataset": "D", "demo": False, "output_dir": str(output_dir), "do_overwrite": False}
    )
    datasets_main.main.__wrapped__(cfg)

    run_in_env.assert_called_once_with(
        f"build {output_dir}",
        str(output_dir),
        env="env",
        do_overwrite=False,
        cwd=build_dir,
    )
