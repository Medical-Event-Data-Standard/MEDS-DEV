import json
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest
from aces.config import PlainPredicateConfig
from meds_testing_helpers.dataset import MEDSDataset
from omegaconf import OmegaConf

from MEDS_DEV import DATASETS
from tests.utils import NAME_AND_DIR, run_command

MAX_UNCOVERED_PREDICATE_CODE_MATCHER_FRACTION = 0.10


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
        name: (config["code"], PlainPredicateConfig(code=config["code"]))
        for name, config in predicates_config["predicates"].items()
        if "expr" not in config
    }

    matchers = {}
    for name, (code_config, predicate) in predicate_code_matchers.items():
        matcher_key = json.dumps(code_config, sort_keys=True)
        matchers.setdefault(matcher_key, {"predicate": predicate, "names": []})["names"].append(name)

    assert matchers, f"Dataset {dataset_name} does not define any plain predicate code matchers"

    data_files = sorted((demo_dataset_dir / "data").rglob("*.parquet"))
    assert data_files, f"No MEDS event files found for demo dataset {dataset_name}"

    coverage = (
        pl.scan_parquet([str(path) for path in data_files])
        .select(
            matcher["predicate"].MEDS_eval_expr().fill_null(False).any().alias(f"matcher_{i}")
            for i, matcher in enumerate(matchers.values())
        )
        .collect()
        .row(0, named=True)
    )

    uncovered = [
        (matcher_key, matcher["names"])
        for i, (matcher_key, matcher) in enumerate(matchers.items())
        if not coverage[f"matcher_{i}"]
    ]
    uncovered_fraction = len(uncovered) / len(matchers)
    uncovered_details = "\n".join(
        f"  - {matcher_key} (predicates: {', '.join(names)})" for matcher_key, names in uncovered
    )

    if uncovered:
        warnings.warn(
            f"Dataset {dataset_name} demo does not cover {len(uncovered)}/{len(matchers)} "
            f"({uncovered_fraction:.1%}) unique predicate code matchers:\n{uncovered_details}",
            stacklevel=1,
        )

    assert uncovered_fraction <= MAX_UNCOVERED_PREDICATE_CODE_MATCHER_FRACTION, (
        f"Dataset {dataset_name} demo leaves {uncovered_fraction:.1%} of unique predicate code matchers "
        f"uncovered, exceeding the allowed "
        f"{MAX_UNCOVERED_PREDICATE_CODE_MATCHER_FRACTION:.1%}:\n{uncovered_details}"
    )
