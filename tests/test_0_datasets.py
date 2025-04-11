from pathlib import Path
from tempfile import TemporaryDirectory

from meds_testing_helpers.dataset import MEDSDataset

from MEDS_DEV import DATASETS
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


def test_datasets_configured(demo_dataset: NAME_AND_DIR):
    dataset_name, demo_dataset_dir = demo_dataset

    # Check validity
    try:
        MEDSDataset(root_dir=demo_dataset_dir)
    except Exception as e:
        raise AssertionError(f"Failed to validate dataset {dataset_name} from {demo_dataset_dir}") from e
