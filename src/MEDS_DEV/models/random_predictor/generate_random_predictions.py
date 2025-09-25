import logging
from importlib.resources import files
from pathlib import Path

import hydra
import meds
import numpy as np
import polars as pl
from meds_evaluation.schema import (
    PREDICTED_BOOLEAN_PROBABILITY_FIELD,
    PREDICTED_BOOLEAN_VALUE_FIELD,
    validate_binary_classification_schema,
)
from omegaconf import DictConfig

logger = logging.getLogger(__name__)

CONFIG = files("MEDS_DEV") / "models" / "random_predictor" / "_config.yaml"


@hydra.main(version_base=None, config_path=str(CONFIG.parent.resolve()), config_name=CONFIG.stem)
def main(cfg: DictConfig) -> None:
    """Generates random predictions for the specified split (must be held-out) of a dataset.

    Args:
        cfg: The configuration object, controlled through Hydra command line arguments. Takes:
          - dataset_dir: The directory containing the dataset.
          - labels_dir: The directory containing the labels.
          - predictions_fp: The file path to write the predictions to.
          - seed: The random seed to use for generating predictions.
          - split: The split to generate predictions for. Must be the held-out split.

    Returns:
        None. Writes the predictions to the specified file path.

    Raises:
        FileNotFoundError: If the splits file or labels file(s) cannot be found.
        ValueError: If the specified split does not match the held-out split or if labels cannot be read.

    Examples:
    Note these are in python doctest format; however, in practice this will be run via the Hydra CLI.

    >>> cfg = DictConfig({
    ...     "split": "train",
    ...     "dataset_dir": "data/dataset",
    ...     "labels_dir": "data/labels",
    ...     "predictions_fp": "data/predictions.parquet",
    ...     "seed": 42,
    ... })
    >>> main(cfg)
    Traceback (most recent call last):
        ...
    ValueError: Split train does not match ...

    >>> import tempfile, os
    >>> with tempfile.TemporaryDirectory() as tmp_dir:
    ...     cfg = DictConfig({
    ...         "split": "held_out",
    ...         "dataset_dir": os.path.join(tmp_dir, "dataset"),
    ...         "labels_dir": os.path.join(tmp_dir, "labels"),
    ...         "predictions_fp": os.path.join(tmp_dir, "predictions.parquet"),
    ...         "seed": 42,
    ...     })
    ...     main(cfg)
    Traceback (most recent call last):
        ...
    FileNotFoundError: Could not find splits file metadata/subject_splits.parquet for dataset ...

    >>> subject_splits = pl.DataFrame({"subject_id": [1, 2, 3], "split": ["held_out", "held_out", "train"]})
    >>> with tempfile.TemporaryDirectory() as tmp_dir:
    ...     root_dir = Path(tmp_dir)
    ...     dataset_dir = root_dir / "dataset"
    ...     subject_splits_fp = dataset_dir / "metadata" / "subject_splits.parquet"
    ...     subject_splits_fp.parent.mkdir(parents=True)
    ...     subject_splits.write_parquet(subject_splits_fp)
    ...     predictions_fp = root_dir / "predictions.parquet"
    ...     cfg = DictConfig({
    ...         "split": "held_out",
    ...         "dataset_dir": str(dataset_dir),
    ...         "labels_dir": str(root_dir / "labels"),
    ...         "predictions_fp": str(predictions_fp),
    ...         "seed": 42,
    ...     })
    ...     main(cfg) # will not write anything since no labels are found
    ...     assert not predictions_fp.is_file()

    >>> with tempfile.TemporaryDirectory() as tmp_dir:
    ...     root_dir = Path(tmp_dir)
    ...     dataset_dir = root_dir / "dataset"
    ...     subject_splits_fp = dataset_dir / "metadata" / "subject_splits.parquet"
    ...     subject_splits_fp.parent.mkdir(parents=True)
    ...     subject_splits.write_parquet(subject_splits_fp)
    ...     labels_dir = root_dir / "labels"
    ...     labels_dir.mkdir()
    ...     labels_fp = labels_dir / "labels.parquet"
    ...     labels_fp.write_text("THIS IS INVALID!")
    ...     cfg = DictConfig({
    ...         "split": "held_out",
    ...         "dataset_dir": str(dataset_dir),
    ...         "labels_dir": str(labels_dir),
    ...         "predictions_fp": str(root_dir / "predictions.parquet"),
    ...         "seed": 42,
    ...     })
    ...     main(cfg)
    Traceback (most recent call last):
        ...
    ValueError: Error reading labels: ...

    >>> _ = pl.Config.set_tbl_width_chars(130)
    >>> from datetime import datetime
    >>> labels = pl.DataFrame({
    ...     "subject_id": [1, 2, 3],
    ...     "prediction_time": [datetime(2021, 1, 1), datetime(2021, 1, 2), datetime(2021, 1, 3)],
    ...     "boolean_value": [False, True, False],
    ... })
    >>> with tempfile.TemporaryDirectory() as tmp_dir:
    ...     root_dir = Path(tmp_dir)
    ...     dataset_dir = root_dir / "dataset"
    ...     subject_splits_fp = dataset_dir / "metadata" / "subject_splits.parquet"
    ...     subject_splits_fp.parent.mkdir(parents=True)
    ...     subject_splits.write_parquet(subject_splits_fp)
    ...     labels_dir = root_dir / "labels"
    ...     labels_dir.mkdir()
    ...     labels_fp = labels_dir / "labels.parquet"
    ...     labels.write_parquet(labels_fp)
    ...     predictions_fp = root_dir / "predictions.parquet"
    ...     cfg = DictConfig({
    ...         "split": "held_out",
    ...         "dataset_dir": str(dataset_dir),
    ...         "labels_dir": str(labels_dir),
    ...         "predictions_fp": str(predictions_fp),
    ...         "seed": 42,
    ...     })
    ...     main(cfg)
    ...     predictions = pl.read_parquet(predictions_fp)
    ...     predictions
    shape: (2, 5)
    ┌────────────┬─────────────────────┬───────────────┬───────────────────────────────┬─────────────────────────┐
    │ subject_id ┆ prediction_time     ┆ boolean_value ┆ predicted_boolean_probability ┆ predicted_boolean_value │
    │ ---        ┆ ---                 ┆ ---           ┆ ---                           ┆ ---                     │
    │ i64        ┆ datetime[μs]        ┆ bool          ┆ f64                           ┆ bool                    │
    ╞════════════╪═════════════════════╪═══════════════╪═══════════════════════════════╪═════════════════════════╡
    │ 1          ┆ 2021-01-01 00:00:00 ┆ false         ┆ 0.773956                      ┆ true                    │
    │ 2          ┆ 2021-01-02 00:00:00 ┆ true          ┆ 0.438878                      ┆ false                   │
    └────────────┴─────────────────────┴───────────────┴───────────────────────────────┴─────────────────────────┘
    """  # noqa: E501

    dataset_dir = Path(cfg.dataset_dir)
    labels_dir = Path(cfg.labels_dir)
    predictions_fp = Path(cfg.predictions_fp)
    predictions_fp.parent.mkdir(parents=True, exist_ok=True)
    seed = cfg.seed

    if cfg.split != meds.held_out_split:
        raise ValueError(
            f"Split {cfg.split} does not match held out split {meds.held_out_split}; this model should "
            "only be used for predictions so this is likely an error!"
        )

    splits_file = dataset_dir / meds.subject_splits_filepath
    if not splits_file.is_file():
        raise FileNotFoundError(
            f"Could not find splits file {splits_file.relative_to(dataset_dir)} for dataset {dataset_dir}."
        )

    splits = pl.read_parquet(splits_file, use_pyarrow=True)
    subjects = set(splits.filter(pl.col("split") == cfg.split)[meds.subject_id_field])

    # Labels can live in any parquet file within the labels directory:
    labels_files = list(labels_dir.rglob("*.parquet"))
    if not labels_files:
        logger.warning(f"No labels found in {labels_dir}. Exiting without writing.")
        return

    def read_split(fp: Path) -> pl.DataFrame:
        return pl.read_parquet(fp, use_pyarrow=True).filter(pl.col(meds.subject_id_field).is_in(subjects))

    try:
        labels = pl.concat([read_split(f) for f in labels_files], how="vertical_relaxed")
    except Exception as e:
        err_lines = [f"Error reading labels: {e}", "Labels dir contents:"]
        for file in labels_dir.rglob("*.parquet"):
            err_lines.append(f"  - {file.relative_to(labels_dir)}")
        err_str = "\n".join(err_lines)
        logger.error(err_str)
        raise ValueError(err_str) from e

    rng = np.random.default_rng(seed)
    probabilities = rng.uniform(0, 1, len(labels))

    predictions = labels.with_columns(
        pl.Series(probabilities).alias(PREDICTED_BOOLEAN_PROBABILITY_FIELD),
    )
    predictions = predictions.with_columns(
        (pl.col(PREDICTED_BOOLEAN_PROBABILITY_FIELD) > 0.5).alias(PREDICTED_BOOLEAN_VALUE_FIELD),
    )

    # Check the schema output:
    validate_binary_classification_schema(predictions)

    predictions.write_parquet(predictions_fp, use_pyarrow=True)


if __name__ == "__main__":
    main()
