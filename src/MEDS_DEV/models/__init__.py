import itertools
from collections.abc import Generator
from enum import StrEnum, auto
from importlib.resources import files
from pathlib import Path

import meds
from omegaconf import DictConfig, OmegaConf

from ..tasks import TASKS
from ..utils import Metadata
from . import sources
from .sources import SOURCE_FILENAME, Fetcher, parse_source, read_source_file, resolve_source
from .steps import load_step_graph

model_files = files("MEDS_DEV.models")
CFG_YAML = files("MEDS_DEV.configs") / "_run_model.yaml"

MODELS = {}


def load_model_yaml(model_yaml: Path, model_name: str) -> dict:
    """Loads and validates a `model.yaml` (either schema version) into a registry entry."""
    entry = OmegaConf.to_object(OmegaConf.load(model_yaml))
    entry["metadata"] = Metadata(**entry["metadata"])
    # Version 1 files are run by `model_commands`; version 2 files by `MEDS_DEV.models.steps`. Both are
    # described by a step graph, which also validates version 2 files when the registry is loaded.
    entry["schema_version"] = entry.get("schema_version", 1)
    try:
        entry["step_graph"] = load_step_graph(entry)
    except ValueError as e:
        raise ValueError(f"Invalid model.yaml for model {model_name} ({model_yaml}): {e}") from e
    return entry


for path in model_files.rglob("*/model.yaml"):
    model_name = path.relative_to(model_files).parent.with_suffix("").as_posix()
    MODELS[model_name] = load_model_yaml(path, model_name)
    requirements_path = path.parent / "requirements.txt"
    MODELS[model_name]["requirements"] = requirements_path if requirements_path.exists() else None
    MODELS[model_name]["model_dir"] = path.parent


def register_source_models(models_root: Path, models: dict) -> None:
    """Adds the models registered by reference (a `source.yaml`) under `models_root` to `models`.

    Only `source.yaml` is read; the model's own model.yaml is fetched (or read from the cache) by `get_model`,
    so importing MEDS-DEV needs no network. See `MEDS_DEV.models.sources`.
    """
    for path in models_root.rglob(f"*/{SOURCE_FILENAME}"):
        model_name = path.relative_to(models_root).parent.with_suffix("").as_posix()
        if model_name in models:
            raise ValueError(
                f"Model {model_name} has both a model.yaml and a {SOURCE_FILENAME}; keep only one."
            )
        try:
            source = read_source_file(path)
        except ValueError as e:
            raise ValueError(f"Invalid {SOURCE_FILENAME} for model {model_name} ({path}): {e}") from e
        models[model_name] = {"source": source, "model_dir": path.parent}


register_source_models(Path(str(model_files)), MODELS)


def get_model(model_name: str, cache_dir: Path | None = None, fetch: Fetcher | None = None) -> dict:
    r"""Returns the full registry entry of a model, fetching a `source.yaml` model's files if needed.

    For models with a local `model.yaml`, this is `MODELS[model_name]`. For models registered through a
    `source.yaml`, the pinned `model.yaml` is fetched once (or read from the cache), verified and validated,
    and the entry gains `metadata`, `schema_version`, `step_graph`, `commands`/`steps` and `requirements`
    (the generated requirements file in the cache).

    Examples:
        >>> import hashlib, tempfile
        >>> model_yaml = b"metadata: {description: d, contacts: [{name: n}]}\ncommands: {supervised: {predict: p}}\n"
        >>> source = parse_source({
        ...     "repo": "https://github.com/org/m", "ref": "a" * 40, "profile": "probe",
        ...     "sha256": hashlib.sha256(model_yaml).hexdigest(), "requirements": ["pkg"],
        ... })
        >>> MODELS["_doctest/remote"] = {"source": source, "model_dir": Path("models/_doctest/remote")}
        >>> with tempfile.TemporaryDirectory() as d:
        ...     entry = get_model("_doctest/remote", cache_dir=Path(d), fetch=lambda url: model_yaml)
        ...     requirements = entry["requirements"].read_text()
        ...     print(entry["metadata"].description, entry["schema_version"], requirements)
        d 1 pkg
        <BLANKLINE>
        >>> del MODELS["_doctest/remote"]
    """  # noqa: E501
    if model_name not in MODELS:
        raise ValueError(f"Model {model_name} not currently configured. Available models: {MODELS.keys()}")
    entry = MODELS[model_name]
    if "source" in entry and "step_graph" not in entry:
        resolved_dir = resolve_source(entry["source"], cache_dir=cache_dir, fetch=fetch or sources.http_fetch)
        entry.update(load_model_yaml(resolved_dir / "model.yaml", model_name))
        entry["requirements"] = resolved_dir / "requirements.txt"
    return entry


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


def task_criteria_path(task_name: str | None, explicit_path: str | Path | None = None) -> str | None:
    """Returns a task's ACES criteria file: `explicit_path` if set, else the registered file of `task_name`.

    Examples:
        >>> task_criteria_path("not/a/task", "local/criteria.yaml")
        'local/criteria.yaml'
        >>> task_criteria_path("not/a/task") is None
        True
        >>> task_criteria_path(None) is None
        True
    """
    if explicit_path:
        return str(explicit_path)
    if task_name in TASKS:
        return str(TASKS[task_name]["criteria_fp"])
    return None


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

    Models that need a dataset's predicates file (e.g., for featurization) can use the optional
    `predicates_path` template variable, which is populated when `predicates_path` is set in the config:
        >>> cfg.predicates_path = "predicates.yaml"
        >>> commands["supervised"]["train"] = (
        ...     "FT data={dataset_dir} labels={labels_dir} output={output_dir} predicates={predicates_path}"
        ... )
        >>> list(model_commands(cfg, commands, model_dir))
        [('FT data=data labels=labels output=output predicates=predicates.yaml', PosixPath('output'))]

    If a model command needs the variable but the caller does not provide it, command formatting fails
    immediately instead of running the model without its required predicates:
        >>> cfg.predicates_path = None
        >>> list(model_commands(cfg, commands, model_dir))
        Traceback (most recent call last):
            ...
        KeyError: 'predicates_path'

    Models that predict a task without being trained on its labels (e.g., zero-shot models) need the task
    definition itself. The optional `task_criteria_path` template variable is the ACES criteria file of the
    task; it pairs with `predicates_path` exactly as in `meds-dev-task`. An explicit `task_criteria_path`
    is used as given:
        >>> cfg.task_criteria_path = "task.yaml"
        >>> commands["supervised"]["train"] = "ZS labels={labels_dir} task={task_criteria_path}"
        >>> list(model_commands(cfg, commands, model_dir))
        [('ZS labels=labels task=task.yaml', PosixPath('output'))]

    Otherwise, it is the registered criteria file of `task_name`, i.e., the file `meds-dev-task` extracted the
    labels with:
        >>> cfg.task_criteria_path = None
        >>> cfg.task_name = "mortality/in_icu/first_24h"
        >>> ((command, _),) = model_commands(cfg, commands, model_dir)
        >>> command.endswith("tasks/mortality/in_icu/first_24h.yaml")
        True

    As with `predicates_path`, a command that needs the variable fails if no task is given or registered:
        >>> cfg.task_name = "not/a/task"
        >>> list(model_commands(cfg, commands, model_dir))
        Traceback (most recent call last):
            ...
        KeyError: 'task_criteria_path'

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
    if cfg.get("predicates_path", None):
        format_kwargs["predicates_path"] = str(cfg.predicates_path)
    criteria_fp = task_criteria_path(cfg.get("task_name", None), cfg.get("task_criteria_path", None))
    if criteria_fp:
        format_kwargs["task_criteria_path"] = str(criteria_fp)
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


__all__ = [
    "CFG_YAML",
    "MODELS",
    "DatasetType",
    "RunMode",
    "get_model",
    "model_commands",
    "task_criteria_path",
]
