r"""The FEMR count baseline: FEMR's age and count featurizers, followed by an XGBoost classifier.

This follows FEMR's tutorial "Count Featurization And Modeling" (som-shahlab/femr). The featurization is
FEMR's own code, called unchanged; this script only connects it to MEDS-DEV:

- `train` fits FEMR's featurizers and `xgboost.XGBClassifier()` on the labels of the train split;
- `predict` featurizes the labels of a split with the fitted featurizers and scores them.

Both read a `meds_reader` database of the dataset, built by the model's `preprocess_data` step.

Usage:
    python femr_count.py train <meds_reader_dir> <labels_dir> <model_dir> <num_threads>
    python femr_count.py predict <meds_reader_dir> <labels_dir> <model_dir> <split> <predictions_fp> \
        <num_threads>
"""

import pickle
import sys
from pathlib import Path

import polars as pl

KEYS = ["subject_id", "prediction_time"]
FEATURIZERS_FILE = "featurizers.pkl"
MODEL_FILE = "xgboost.json"
SEED = 1


def read_labels(labels_dir: Path, meds_reader_dir: Path, split: str) -> pl.DataFrame:
    """Returns the labels of the subjects of a split, sorted by subject and prediction time.

    The split of a label is the split of its subject in the dataset, whatever the layout of `labels_dir`.

    Examples:
        >>> import tempfile
        >>> from datetime import datetime
        >>> with tempfile.TemporaryDirectory() as d:
        ...     labels_dir, meds_reader_dir = Path(d) / "labels", Path(d) / "meds_reader"
        ...     (labels_dir / "any").mkdir(parents=True)
        ...     (meds_reader_dir / "metadata").mkdir(parents=True)
        ...     pl.DataFrame({
        ...         "subject_id": [3, 1, 2],
        ...         "prediction_time": [datetime(2020, 1, 3), datetime(2020, 1, 1), datetime(2020, 1, 2)],
        ...         "boolean_value": [True, False, True],
        ...     }).write_parquet(labels_dir / "any" / "0.parquet")
        ...     splits = pl.DataFrame({"subject_id": [1, 2, 3], "split": ["train", "held_out", "train"]})
        ...     splits.write_parquet(meds_reader_dir / "metadata" / "subject_splits.parquet")
        ...     read_labels(labels_dir, meds_reader_dir, "train")
        shape: (2, 3)
        ┌────────────┬─────────────────────┬───────────────┐
        │ subject_id ┆ prediction_time     ┆ boolean_value │
        │ ---        ┆ ---                 ┆ ---           │
        │ i64        ┆ datetime[μs]        ┆ bool          │
        ╞════════════╪═════════════════════╪═══════════════╡
        │ 1          ┆ 2020-01-01 00:00:00 ┆ false         │
        │ 3          ┆ 2020-01-03 00:00:00 ┆ true          │
        └────────────┴─────────────────────┴───────────────┘
    """
    splits = pl.read_parquet(meds_reader_dir / "metadata" / "subject_splits.parquet")
    subjects = splits.filter(pl.col("split") == split)["subject_id"]
    labels = pl.concat(
        [
            pl.read_parquet(fp, columns=[*KEYS, "boolean_value"])
            for fp in sorted(labels_dir.rglob("*.parquet"))
        ]
    )
    labels = labels.filter(pl.col("subject_id").is_in(subjects.implode())).sort(KEYS)
    if labels.is_empty():
        raise ValueError(f"No labels found in {labels_dir} for the subjects of split {split}.")
    return labels


def train(meds_reader_dir: Path, labels_dir: Path, model_dir: Path, num_threads: int) -> None:
    # Imported here because they are installed in the model's environment, not in MEDS-DEV's.
    import femr.featurizers
    import meds_reader
    import xgboost

    labels = read_labels(labels_dir, meds_reader_dir, "train").to_pandas()

    # The tutorial's featurizers: age (not normalized) and code counts, with one column per (code, text) pair.
    featurizers = femr.featurizers.FeaturizerList(
        [
            femr.featurizers.AgeFeaturizer(is_normalize=False),
            femr.featurizers.CountFeaturizer(string_value_combination=True),
        ]
    )
    with meds_reader.SubjectDatabase(str(meds_reader_dir), num_threads=num_threads) as database:
        # The tutorial fits the vocabulary on every labelled subject; here, only the train split is used.
        featurizers.preprocess_featurizers(database, labels)
        features = featurizers.featurize(database, labels)
    training = femr.featurizers.join_labels(features, labels)

    model = xgboost.XGBClassifier(random_state=SEED, n_jobs=num_threads)
    model.fit(training["features"], training["boolean_values"])

    model_dir.mkdir(parents=True, exist_ok=True)
    with (model_dir / FEATURIZERS_FILE).open("wb") as f:
        pickle.dump(featurizers, f)
    model.save_model(model_dir / MODEL_FILE)


def predict(
    meds_reader_dir: Path,
    labels_dir: Path,
    model_dir: Path,
    split: str,
    predictions_fp: Path,
    num_threads: int,
) -> None:
    import meds_reader
    import xgboost

    labels = read_labels(labels_dir, meds_reader_dir, split)
    with (model_dir / FEATURIZERS_FILE).open("rb") as f:
        featurizers = pickle.load(f)
    model = xgboost.XGBClassifier()
    model.load_model(model_dir / MODEL_FILE)

    with meds_reader.SubjectDatabase(str(meds_reader_dir), num_threads=num_threads) as database:
        features = featurizers.featurize(database, labels.select(KEYS).to_pandas())
    probabilities = model.predict_proba(features["features"])[:, 1]

    # FEMR returns the keys of its feature rows, so predictions are matched to labels by key, not by order.
    scores = pl.DataFrame(
        {
            "subject_id": features["subject_ids"],
            "prediction_time": features["feature_times"],
            "predicted_boolean_probability": probabilities.astype("float64"),
        }
    ).with_columns(pl.col("prediction_time").cast(labels.schema["prediction_time"]))
    predictions = labels.join(
        scores, on=KEYS, how="inner", validate="1:1", maintain_order="left"
    ).with_columns(
        predicted_boolean_value=pl.col("predicted_boolean_probability") > 0.5  # the tutorial's decision rule
    )
    if predictions.height != labels.height or scores.height != labels.height:
        raise ValueError(f"FEMR featurized {scores.height} of the {labels.height} labels of split {split}.")

    predictions_fp.parent.mkdir(parents=True, exist_ok=True)
    predictions.select(
        *KEYS, "boolean_value", "predicted_boolean_value", "predicted_boolean_probability"
    ).write_parquet(predictions_fp)


if __name__ == "__main__":
    command, *args = sys.argv[1:]
    if command == "train":
        meds_reader_dir, labels_dir, model_dir, num_threads = args
        train(Path(meds_reader_dir), Path(labels_dir), Path(model_dir), int(num_threads))
    elif command == "predict":
        meds_reader_dir, labels_dir, model_dir, split, predictions_fp, num_threads = args
        predict(
            Path(meds_reader_dir),
            Path(labels_dir),
            Path(model_dir),
            split,
            Path(predictions_fp),
            int(num_threads),
        )
    else:
        raise SystemExit(f"Unknown command {command!r}; expected 'train' or 'predict'.")
