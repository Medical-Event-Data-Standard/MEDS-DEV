import itertools
from collections.abc import Generator
from enum import StrEnum, auto
from importlib.resources import files
from pathlib import Path

import meds
from omegaconf import DictConfig, OmegaConf

from ..utils import Metadata

model_files = files("MEDS_DEV.models")
CFG_YAML = files("MEDS_DEV.configs") / "_run_model.yaml"

MODELS = {}

for path in model_files.rglob("*/model.yaml"):
    model_name = path.relative_to(model_files).parent.with_suffix("").as_posix()
    MODELS[model_name] = OmegaConf.to_object(OmegaConf.load(path))
    MODELS[model_name]["metadata"] = Metadata(**MODELS[model_name]["metadata"])
    requirements_path = path.parent / "requirements.txt"
    MODELS[model_name]["requirements"] = requirements_path if requirements_path.exists() else None
    MODELS[model_name]["model_dir"] = path.parent


class RunMode(StrEnum):
    """The different run modes supported.

    Args:
        TRAIN: Train a model.
        PREDICT: Predict with a model.
        FULL: Perform all viable stages for a model.
    """

    TRAIN = auto()
    PREDICT = auto()
    FULL = auto()


ALL_RUN_MODES = [RunMode.TRAIN, RunMode.PREDICT]


class DatasetType(StrEnum):
    """The different dataset types supported.

    Args:
        UNSUPERVISED: Unsupervised dataset.
        SUPERVISED: Supervised dataset.
        FULL: Run the model across both the unsupervised and supervised datasets.
    """

    UNSUPERVISED = auto()
    SUPERVISED = auto()
    FULL = auto()


ALL_DATASET_TYPES = [DatasetType.UNSUPERVISED, DatasetType.SUPERVISED]

COMMANDS_DICT_T = dict[str, dict[str, str]]


def fmt_command(
    commands: COMMANDS_DICT_T,
    dataset_type: DatasetType,
    run_mode: RunMode,
    **format_kwargs,
) -> str:
    """Gets the appropriate model command for the given run mode and commands dictionary.

    Args:
        commands: The dictionary of commands for the model. These are stored in the model folder in
            `model.yaml` in the `commands` key and are loaded for the correct model from the MODELS
            dictionary.
        dataset_type: The dataset type to use.
        run_mode: The run mode to use.
        format_kwargs: The remaining template variables to format the command.

    Returns:
        The command to run the model.

    Raises:
        RuntimeError: If the model does not support the given dataset type or run mode.

    Examples:
        >>> commands = {
        ...     "unsupervised": {"train": "train {dataset_dir} {output_dir}"},
        ...     "supervised": {
        ...         "train": "FT data={dataset_dir} labels={labels_dir} output={output_dir}",
        ...         "predict": "predict model_initialization_dir={model_dir} labels={labels_dir}",
        ...     },
        ... }
        >>> fmt_command(commands, "unsupervised", "train", dataset_dir="data", output_dir="output")
        'train data output'
        >>> fmt_command(commands, "supervised", "predict", model_dir="model", labels_dir="labels")
        'predict model_initialization_dir=model labels=labels'

    You can also use the constants in the enumeration objects:
        >>> fmt_command(
        ...     commands, DatasetType.UNSUPERVISED, RunMode.TRAIN, dataset_dir="data2", output_dir="output2"
        ... )
        'train data2 output2'

    Extra format variables are ignored:
        >>> fmt_command(commands, "supervised", "predict", model_dir="model", labels_dir="labels", out="foo")
        'predict model_initialization_dir=model labels=labels'

    Unsupported commands cause errors:
        >>> fmt_command(commands, "semi-supervised", "predict")
        Traceback (most recent call last):
            ...
        RuntimeError: Model does not support dataset type semi-supervised.
        >>> fmt_command(commands, "supervised", "full")
        Traceback (most recent call last):
            ...
        RuntimeError: Model does not support run mode full.
    """

    if dataset_type not in commands:
        raise RuntimeError(f"Model does not support dataset type {dataset_type}.")

    dataset_commands = commands[dataset_type]
    if run_mode not in dataset_commands:
        raise RuntimeError(f"Model does not support run mode {run_mode}.")

    return commands[dataset_type][run_mode].format(**format_kwargs)


def model_commands(
    cfg: DictConfig, commands: dict[str, dict[str, str]], model_dir: Path
) -> Generator[tuple[str, Path]]:
    """Yields the sequence of appropriate dataset, run mode pairs for the given config and commands.

    For a given model run, the configuration may specify to either run a single command or a sequence of
    commands that span multiple (supported) dataset types and run modes. This function yields the appropriate
    sequence of commands to use for the given configuration and model. This sequence may be a single command
    or multiple, and is returned as a generator of tuples of the individual commands and command-specific
    output directories. If the configuration dictates a single run, the output directory will be the specified
    output directory (specified in the config), but if the configuration specifies multiple runs, the
    command-specific output directories will be subdirectories of `output_dir` based on which command is being
    run. In particular, if a command reflects running over dataset type `DATASET_TYPE` and run mode
    `RUN_MODE`, the output directory will be `f"output_dir/{DATASET_TYPE}/{RUN_MODE}"`.

    The configuration indicates that a sequence of commands should be run if either or both of the `cfg.mode`
    and `cfg.dataset_type` are set to `RunMode.FULL` (`"full"`) and `DatasetType.FULL` (`"full"`),
    respectively. Otherwise, only the single specified combination of run mode and dataset type will be run.
    If dataset type is set to `DatasetType.FULL`, the model will be run over both the unsupervised and
    supervised dataset types, in that order (or whichever of those are supported by the model), for the
    specified run mode (or sequence therein). If the run mode is set to full, the model will be run over both
    the "train" and "predict" run modes, in that order (or whichever of those are supported by the model),
    within all specified dataset types.

    Args:
        cfg: The configuration for the model run.
        commands: The dictionary of commands for the model. These are stored in the model folder in the
            `model.yaml` in the `commands` key and are loaded for the correct model from the MODELS variable.
        model_dir: The directory on disk of the model's configuration files in MEDS-DEV.

    Yields:
        The sequence of base commands (un-formatted) to run for the given model run.

    Raises:
        ValueError: If the configuration specifies a split while the run mode is `RunMode.FULL`. This
        constitutes and error because the split must be set dynamically in run model `RunMode.FULL` as it
        varies across the individual commands.

    Examples:
        >>> cfg = DictConfig({
        ...     "mode": "train",
        ...     "dataset_type": "supervised",
        ...     "dataset_dir": "data",
        ...     "labels_dir": "labels",
        ...     "output_dir": "output",
        ...     "demo": False,
        ... })
        >>> commands = {
        ...     "unsupervised": {"train": "train {dataset_dir} {output_dir}"},
        ...     "supervised": {
        ...         "train": "FT data={dataset_dir} labels={labels_dir} output={output_dir}",
        ...         "predict": "predict model_initialization_dir={model_dir} labels={labels_dir}",
        ...     },
        ... }
        >>> model_dir = "model_dir"
        >>> list(model_commands(cfg, commands, model_dir))
        [('FT data=data labels=labels output=output', PosixPath('output'))]

    Other configuration arguments get passed through, like `model_initialization_dir`, though they only appear
    in the final command if their format args exist.
        >>> cfg.model_initialization_dir = "foobar"
        >>> list(model_commands(cfg, commands, model_dir))
        [('FT data=data labels=labels output=output', PosixPath('output'))]

    The system errors if a split is set but it is in full mode.
        >>> cfg.split = "tuning"
        >>> cfg.mode = "full"
        >>> list(model_commands(cfg, commands, model_dir))
        Traceback (most recent call last):
            ...
        ValueError: Cannot set split manually when mode is full.
    """

    run_modes = ALL_RUN_MODES if cfg.mode == RunMode.FULL else [cfg.mode]
    dataset_types = ALL_DATASET_TYPES if cfg.dataset_type == DatasetType.FULL else [cfg.dataset_type]

    do_set_split = cfg.mode == RunMode.FULL

    output_dir = Path(cfg.output_dir)

    format_kwargs = {
        "dataset_dir": str(cfg.dataset_dir),
        "model_dir": str(model_dir),
        "demo": cfg.get("demo", False),
    }
    if cfg.get("model_initialization_dir", None):
        format_kwargs["model_initialization_dir"] = cfg.model_initialization_dir
    if cfg.get("split", None):
        if do_set_split:
            raise ValueError(f"Cannot set split manually when mode is {cfg.mode}.")
        format_kwargs["split"] = cfg.split

    if len(run_modes) == 1 and len(dataset_types) == 1:
        run_mode = run_modes[0]
        dataset_type = dataset_types[0]
        format_kwargs["output_dir"] = str(output_dir)
        if dataset_type == DatasetType.SUPERVISED:
            format_kwargs["labels_dir"] = str(cfg.labels_dir)
        yield fmt_command(commands, dataset_type, run_mode, **format_kwargs), output_dir
        return

    all_modes = itertools.product(run_modes, dataset_types)
    for run_mode, dataset_type in all_modes:
        dataset_commands = commands.get(dataset_type)
        if dataset_commands is None:
            continue

        run_command = dataset_commands.get(run_mode, None)
        if not run_command:
            continue

        run_output_dir = output_dir / cfg.dataset_name
        if dataset_type == DatasetType.SUPERVISED:
            run_output_dir = run_output_dir / cfg.task_name
            format_kwargs["labels_dir"] = str(cfg.labels_dir)
        else:
            run_output_dir = run_output_dir / dataset_type

        run_output_dir = run_output_dir / run_mode

        format_kwargs["output_dir"] = str(run_output_dir)

        if do_set_split:
            if run_mode == RunMode.PREDICT:
                format_kwargs["split"] = meds.held_out_split
            else:
                # We don't set the split in anything but predict mode.
                format_kwargs.pop("split", None)

        yield (
            fmt_command(commands, dataset_type, run_mode, **format_kwargs),
            run_output_dir,
        )

        if run_mode != RunMode.PREDICT:
            format_kwargs["model_initialization_dir"] = str(run_output_dir)


__all__ = ["CFG_YAML", "MODELS", "DatasetType", "RunMode", "model_commands"]
