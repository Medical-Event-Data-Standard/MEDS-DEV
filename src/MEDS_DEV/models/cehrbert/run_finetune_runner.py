"""Runs cehrbert's fine-tuning runner, working around a double conversion of `index_date` in cehrbert 1.5.

Since cehrbert 1.5.0, the MEDS mapping stores `index_date` as a POSIX timestamp (a float), but
`HFFineTuningMapping` still passes it to `convert_date_to_posix_time`, which only accepts dates and raises
`ValueError: index_date must be datetime or datetime.datetime`. The error only appears when every record of a
batch has an index date; otherwise cehrbert drops the column first.

This script makes `convert_date_to_posix_time` return timestamps unchanged, then runs
`cehrbert.runners.hf_cehrbert_finetune_runner` exactly as `python -m` would. Remove it, and call the runner
directly again, once a cehrbert release fixes the conversion.

Usage: `python run_finetune_runner.py <finetune.yaml>`
"""

import sys


def accept_timestamps() -> None:
    """Makes cehrbert's `convert_date_to_posix_time` return values that are already timestamps."""
    # Imported here because cehrbert is installed in the model's environment, not in MEDS-DEV's.
    import cehrbert.data_generators.hf_data_generator.hf_dataset_mapping as mapping

    convert_date = mapping.convert_date_to_posix_time

    def convert_date_to_posix_time(index_date):
        if isinstance(index_date, int | float) and not isinstance(index_date, bool):
            return float(index_date)
        return convert_date(index_date)

    mapping.convert_date_to_posix_time = convert_date_to_posix_time


if __name__ == "__main__":
    import runpy

    accept_timestamps()
    sys.argv = ["hf_cehrbert_finetune_runner", *sys.argv[1:]]
    runpy.run_module("cehrbert.runners.hf_cehrbert_finetune_runner", run_name="__main__")
