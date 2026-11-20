"""Writes the predictions of a logistic regression trained by `meds-tab-model`.

`meds-tab-model` writes `<split>_predictions.parquet` for its tree models only: a scikit-learn model is
pickled, but its predictions are not stored. This script scores a split with the pickled model, on the
features the model was trained on (the trial's own configuration is read back from its `config.log`).

Usage: `python predict.py <trial_dir> <split> <predictions_fp>`
"""

import pickle
import sys
from pathlib import Path

import polars as pl


def main(trial_dir: Path, split: str, predictions_fp: Path) -> None:
    # Imported here because they are installed in the model's environment, not in MEDS-DEV's.
    import hydra
    from hydra.core.utils import setup_globals
    from MEDS_tabular_automl.tabular_dataset import TabularDataset
    from omegaconf import OmegaConf

    setup_globals()  # registers the resolvers (e.g., `now`) that the trial's configuration uses
    launcher = hydra.utils.instantiate(OmegaConf.load(trial_dir / "config.log").model_launcher)
    path_cfg = launcher.cfg.path
    with open(trial_dir / f"{path_cfg.model_file_stem}{path_cfg.model_file_extension}", "rb") as f:
        model = pickle.load(f)

    dataset = TabularDataset(launcher.cfg, split=split)
    features, labels = dataset.get_data()
    probabilities = model.predict_proba(features)[:, 1]

    # The tabularized data has one row per label, in the order of the (sorted) label files of the split.
    label_dir = Path(path_cfg.input_label_dir) / split
    label_fps = [(label_dir / shard).with_suffix(".parquet") for shard in dataset._data_shards]
    keys = pl.concat([pl.read_parquet(fp) for fp in label_fps])
    if keys.height != len(probabilities) or (keys["boolean_value"].cast(pl.Int8) != pl.Series(labels)).any():
        raise ValueError(f"The features of split {split} do not match the labels in {label_dir}.")

    predictions = keys.select(
        "subject_id",
        "prediction_time",
        "boolean_value",
        predicted_boolean_value=pl.Series(probabilities > 0.5),
        predicted_boolean_probability=pl.Series(probabilities, dtype=pl.Float64),
    )
    predictions_fp.parent.mkdir(parents=True, exist_ok=True)
    predictions.write_parquet(predictions_fp)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
