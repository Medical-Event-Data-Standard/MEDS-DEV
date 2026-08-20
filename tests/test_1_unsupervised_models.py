from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from MEDS_DEV import MODELS
from tests.utils import NAME_AND_DIR, run_command


def test_non_model_breaks():
    non_model = "_not_supported"
    while non_model in MODELS:
        non_model = f"_{non_model}"

    with TemporaryDirectory() as root_dir:
        output_dir = Path(root_dir) / "output"
        run_command(
            "meds-dev-model",
            test_name="Non-model should error",
            hydra_kwargs={"model": non_model, "output_dir": str(output_dir.resolve())},
            should_error=True,
            want_err_msg=f"Model {non_model} not currently configured",
        )


@pytest.mark.integration
def test_unsupervised(unsupervised_model: NAME_AND_DIR, demo_dataset: NAME_AND_DIR):
    model, final_out_dir = unsupervised_model

    if final_out_dir is None:
        pytest.skip(f"{model} does not support unsupervised training.")
        return

    dataset_name, _ = demo_dataset
    setting = f"Unsupervised {model} on {dataset_name}"

    if not final_out_dir.exists():
        error_lines = [
            f"Output directory {final_out_dir} does not exist for {setting}.",
            f"Model {model} on {dataset_name} did not run properly. Walking back...",
        ]
        d = final_out_dir.parent
        while not d.exists():
            error_lines.append(f"Directory {d} does not exist.")
            d = d.parent
        error_lines.append(f"Directory {d} exists. Contents:")
        error_lines.append(str(list(d.rglob("*"))))
        raise AssertionError("\n".join(error_lines))
