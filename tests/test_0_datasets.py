from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from aces.config import PlainPredicateConfig
from meds_testing_helpers.dataset import MEDSDataset
from omegaconf import OmegaConf

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


@pytest.mark.integration
def test_datasets_configured(demo_dataset: NAME_AND_DIR):
    dataset_name, demo_dataset_dir = demo_dataset

    # Check validity
    try:
        MEDSDataset(root_dir=demo_dataset_dir)
    except Exception as e:
        raise AssertionError(f"Failed to validate dataset {dataset_name} from {demo_dataset_dir}") from e


@pytest.mark.integration
def test_dataset_predicate_codes_covered(demo_dataset: NAME_AND_DIR):
    dataset_name, demo_dataset_dir = demo_dataset
    predicates_path = DATASETS[dataset_name]["predicates"]

    assert predicates_path is not None, f"Dataset {dataset_name} does not define a predicates file"

    predicates_config = OmegaConf.to_container(OmegaConf.load(predicates_path), resolve=True)
    predicate_code_matchers = {
        name: PlainPredicateConfig(code=config["code"])
        for name, config in predicates_config["predicates"].items()
        if "expr" not in config
    }

    data_files = sorted((demo_dataset_dir / "data").rglob("*.parquet"))
    assert data_files, f"No MEDS event files found for demo dataset {dataset_name}"

    coverage = (
        pl.scan_parquet([str(path) for path in data_files])
        .select(
            predicate.MEDS_eval_expr().fill_null(False).any().alias(name)
            for name, predicate in predicate_code_matchers.items()
        )
        .collect()
        .row(0, named=True)
    )
    allowed_uncovered_codes = (
        DATASETS[dataset_name]["testing"].get("demo", {}).get("allowed_uncovered_predicate_codes", {})
    )
    configured_exact_codes = {
        predicate.code for predicate in predicate_code_matchers.values() if isinstance(predicate.code, str)
    }
    unknown_allowed_codes = sorted(set(allowed_uncovered_codes) - configured_exact_codes)
    assert not unknown_allowed_codes, (
        f"Dataset {dataset_name} allows uncovered demo codes that no plain predicate uses:\n"
        + "\n".join(f"  - {code}" for code in unknown_allowed_codes)
    )

    covered_allowed_codes = sorted(
        code
        for code in allowed_uncovered_codes
        if any(
            coverage[name] and predicate.code == code for name, predicate in predicate_code_matchers.items()
        )
    )
    assert not covered_allowed_codes, (
        f"Dataset {dataset_name} demo now covers these allowed-uncovered codes; remove their exceptions:\n"
        + "\n".join(f"  - {code}" for code in covered_allowed_codes)
    )

    uncovered = sorted(
        name
        for name, is_covered in coverage.items()
        if not is_covered
        and not (
            isinstance(predicate_code_matchers[name].code, str)
            and predicate_code_matchers[name].code in allowed_uncovered_codes
        )
    )

    assert not uncovered, (
        f"Dataset {dataset_name} demo does not cover the code matcher for "
        f"{len(uncovered)} plain predicate(s):\n" + "\n".join(f"  - {name}" for name in uncovered)
    )
