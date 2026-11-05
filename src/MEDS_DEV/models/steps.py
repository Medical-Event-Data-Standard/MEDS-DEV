"""Explicit, scoped model steps: version 2 of the `model.yaml` schema.

A version 1 `model.yaml` has four command slots, `unsupervised`/`supervised` x `train`/`predict`. A version 2
`model.yaml` instead lists the model's steps explicitly. Each step declares:

- `scope`: `dataset` (task-independent; run once per dataset and shared by every task) or `task` (run once
  per task);
- `needs`: the earlier steps whose outputs it reads, made available as `{<step>_dir}` template variables;
- `predict: true` on exactly one task-scoped step, whose output holds the predictions to evaluate;
- `command`: the shell command to run.

For example:

```yaml
schema_version: 2
metadata: {...}
profile: probe
steps:
  preprocess_data:
    scope: dataset
    command: my-model preprocess input={dataset_dir} output={step_dir}
  pretrain:
    scope: dataset
    needs: [preprocess_data]
    command: my-model pretrain data={preprocess_data_dir} output={step_dir}
  train_probe:
    scope: task
    needs: [preprocess_data, pretrain]
    command: my-model train encoder={pretrain_dir} labels={labels_dir} output={step_dir}
  predict_probe:
    scope: task
    needs: [preprocess_data, pretrain, train_probe]
    predict: true
    command: my-model predict ... split={split} output={step_dir}
```

Version 1 files remain valid. They are run exactly as before, and `v1_to_step_graph` describes them as an
equivalent step graph for introspection.
"""

import contextlib
import logging
import os
import re
import shutil
import socket
import string
import time
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import meds

logger = logging.getLogger(__name__)

SCHEMA_VERSIONS = (1, 2)

#: Directory (under `<output_dir>/<dataset_name>/`) holding the dataset-scoped steps shared by all tasks.
SHARED_DIR_NAME = "_shared"
#: Directory (under a task's directory) holding the predict step's output for the held-out split.
PREDICT_DIR_NAME = "predict"
#: Subdirectory of a step's run directory that is passed to the step as `{step_dir}`. The run directory
#: itself holds MEDS-DEV's own files (`cmd.sh`, `.done`), so they never mix with the step's artifacts.
STEP_OUTPUT_SUBDIR = "output"

STEP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
#: Step names that would make `{<name>_dir}` collide with another template variable.
RESERVED_STEP_NAMES = frozenset({"dataset", "model", "labels", "step", "model_initialization"})
STEP_KEYS = frozenset({"scope", "needs", "predict", "command"})

COMMON_VARIABLES = frozenset({"dataset_dir", "model_dir", "demo", "predicates_path", "step_dir"})
TASK_VARIABLES = frozenset({"labels_dir", "task_criteria_path"})
PREDICT_VARIABLES = frozenset({"split"})


class Scope(StrEnum):
    """Whether a step depends on the task.

    Args:
        DATASET: Task-independent; run once per dataset and shared by every task (e.g., pre-training).
        TASK: Run once per task; receives the task's `{labels_dir}` and `{task_criteria_path}`.
    """

    DATASET = "dataset"
    TASK = "task"


class Profile(StrEnum):
    """Optional model profiles, matching the MEDS algorithm template. Setting one enables extra checks."""

    SUPERVISED = "supervised"
    FINETUNE = "finetune"
    PROBE = "probe"
    ZERO_SHOT_DIRECT = "zero_shot_direct"
    ZERO_SHOT_MATERIALIZED = "zero_shot_materialized"
    PREDICT_ONLY = "predict_only"


class Overwrite(StrEnum):
    """Which step directories a version 2 run clears before running its steps.

    Args:
        NONE: Clear nothing; finished steps (with a `.done` marker) are skipped.
        TASK: Clear the task-scoped steps of this run; shared dataset-scoped steps are kept.
        ALL: Clear every step this run executes, including shared dataset-scoped steps.
    """

    NONE = "none"
    TASK = "task"
    ALL = "all"


def command_variables(command: str) -> set[str]:
    """Returns the template variables used by a command.

    Examples:
        >>> sorted(command_variables("train data={dataset_dir} out={step_dir} x={pretrain_dir.name}"))
        ['dataset_dir', 'pretrain_dir', 'step_dir']
        >>> command_variables("echo {{literal braces}}")
        set()
        >>> command_variables("echo {}")
        Traceback (most recent call last):
            ...
        ValueError: Positional template fields are not allowed in commands: 'echo {}'
        >>> command_variables("echo {unclosed")
        Traceback (most recent call last):
            ...
        ValueError: Malformed command template 'echo {unclosed': expected '}' before end of string
    """
    try:
        parsed = list(string.Formatter().parse(command))
    except ValueError as e:
        raise ValueError(f"Malformed command template {command!r}: {e}") from e

    names = set()
    for _, field, _, _ in parsed:
        if field is None:
            continue
        name = re.split(r"[.\[]", field, maxsplit=1)[0]
        if not name or name.isdigit():
            raise ValueError(f"Positional template fields are not allowed in commands: {command!r}")
        names.add(name)
    return names


@dataclass(frozen=True)
class Step:
    """One step of a model.

    Examples:
        >>> step = Step("pretrain", Scope.DATASET, "pretrain {preprocess_data_dir} {step_dir}",
        ...             needs=("preprocess_data",))
        >>> sorted(step.variables)
        ['preprocess_data_dir', 'step_dir']
        >>> sorted(step.allowed_variables)
        ['dataset_dir', 'demo', 'model_dir', 'predicates_path', 'preprocess_data_dir', 'step_dir']
    """

    name: str
    scope: Scope
    command: str
    needs: tuple[str, ...] = ()
    predict: bool = False

    @property
    def variables(self) -> set[str]:
        return command_variables(self.command)

    @property
    def allowed_variables(self) -> set[str]:
        allowed = set(COMMON_VARIABLES) | {f"{need}_dir" for need in self.needs}
        if self.scope == Scope.TASK:
            allowed |= TASK_VARIABLES
        if self.predict:
            allowed |= PREDICT_VARIABLES
        return allowed


@dataclass(frozen=True)
class StepGraph:
    """The steps of a model, in declaration order (which is always a valid execution order).

    Examples:
        >>> graph = parse_step_graph({
        ...     "schema_version": 2,
        ...     "steps": {
        ...         "pre": {"scope": "dataset", "command": "pre {dataset_dir} {step_dir}"},
        ...         "fit": {
        ...             "scope": "task", "needs": ["pre"], "command": "fit {pre_dir} {labels_dir} {step_dir}",
        ...         },
        ...         "pred": {
        ...             "scope": "task", "needs": ["pre", "fit"], "predict": True,
        ...             "command": "pred {pre_dir} {fit_dir} {labels_dir} {split} {step_dir}",
        ...         },
        ...     },
        ... })
        >>> [s.name for s in graph.steps]
        ['pre', 'fit', 'pred']
        >>> graph.predict_step.name
        'pred'
        >>> [s.name for s in graph.closure(["fit"])]
        ['pre', 'fit']
        >>> [s.name for s in graph.closure(["fit"], provided={"fit"})]
        ['fit']
    """

    steps: tuple[Step, ...]
    profile: Profile | None = None
    schema_version: int = 2

    @property
    def by_name(self) -> dict[str, Step]:
        return {step.name: step for step in self.steps}

    @property
    def predict_step(self) -> Step | None:
        return next((step for step in self.steps if step.predict), None)

    def closure(self, names: Sequence[str], provided: Collection[str] = ()) -> list[Step]:
        """Returns the named steps and every step they transitively need, in declaration order.

        The needs of `provided` steps (whose outputs already exist, e.g., through `step_dirs`) are not
        followed.
        """
        by_name = self.by_name
        unknown = [name for name in names if name not in by_name]
        if unknown:
            raise ValueError(f"Unknown step(s) {unknown}. Available steps: {list(by_name)}")

        wanted: set[str] = set()
        stack = list(names)
        while stack:
            name = stack.pop()
            if name in wanted:
                continue
            wanted.add(name)
            if name not in provided:
                stack.extend(by_name[name].needs)
        return [step for step in self.steps if step.name in wanted]


def parse_step_graph(spec: Mapping[str, Any]) -> StepGraph:
    """Parses and validates the `steps` (and optional `profile`) of a version 2 `model.yaml`.

    Examples:
        >>> def check(steps, profile=None):
        ...     spec = {"schema_version": 2, "steps": steps}
        ...     if profile:
        ...         spec["profile"] = profile
        ...     try:
        ...         parse_step_graph(spec)
        ...     except ValueError as e:
        ...         print(e)
        >>> pred = {"scope": "task", "predict": True, "command": "p {labels_dir} {split} {step_dir}"}
        >>> check({"pred": pred})
        >>> check({})
        A version 2 model.yaml needs a non-empty `steps` mapping.
        >>> check({"Pred": pred})
        Invalid step name 'Pred': use lowercase letters, digits and underscores, starting with a letter.
        >>> check({"labels": pred})
        Step name 'labels' is reserved.
        >>> check({"x": {"scope": "global", "command": "x"}, "pred": pred})
        Step 'x' has invalid scope 'global'; expected one of ['dataset', 'task'].
        >>> check({"x": {"scope": "task", "cmd": "x"}, "pred": pred})
        Step 'x' has unknown key(s) ['cmd']; allowed keys are ['command', 'needs', 'predict', 'scope'].
        >>> check({"pred": {**pred, "needs": ["later"]}, "later": {"scope": "dataset", "command": "x"}})
        Step 'pred' needs 'later', which is not declared before it.
        >>> check({"t": {"scope": "task", "command": "t"}, "d": {"scope": "dataset", "needs": ["t"], "command": "d"},
        ...        "pred": pred})
        Dataset-scoped step 'd' cannot need task-scoped step 't'.
        >>> check({"x": {"scope": "task", "command": "x {step_dir}"}})
        Exactly one step must set `predict: true`; found 0.
        >>> check({"pred": {**pred, "scope": "dataset"}})
        The predict step 'pred' must be task-scoped.
        >>> check({"predict": {"scope": "task", "command": "x"}, "pred": pred})
        Step name 'predict' is reserved for the directory of the predict step.
        >>> check({"d": {"scope": "dataset", "command": "d {labels_dir}"}, "pred": pred})
        Step 'd' uses undefined template variable(s) ['labels_dir'].
        >>> check({"d": {"scope": "dataset", "command": "d {step_dir}"},
        ...        "pred": {**pred, "command": "p {d_dir} {split}"}})
        Step 'pred' uses undefined template variable(s) ['d_dir'].

    Profiles add checks on the shape of the graph:
        >>> check({"pred": pred}, profile="probe")
        Profile 'probe' needs at least one dataset-scoped (pre-training) step.
        >>> check({"d": {"scope": "dataset", "command": "d"}, "t": {"scope": "task", "command": "t"}, "pred": pred},
        ...       profile="zero_shot_direct")
        Profile 'zero_shot_direct' must not have task-scoped steps other than its predict step; found ['t'].
        >>> check({"d": {"scope": "dataset", "command": "d"}, "pred": pred}, profile="zero_shot_direct")
        Profile 'zero_shot_direct' needs its predict step to use {task_criteria_path}.
        >>> check({"pred": pred}, profile="few_shot")
        Unknown profile 'few_shot'; expected one of ['supervised', 'finetune', 'probe', 'zero_shot_direct', 'zero_shot_materialized', 'predict_only'].
    """  # noqa: E501
    raw_steps = spec.get("steps")
    if not isinstance(raw_steps, Mapping) or not raw_steps:
        raise ValueError("A version 2 model.yaml needs a non-empty `steps` mapping.")

    steps: list[Step] = []
    declared: dict[str, Step] = {}
    for name, raw in raw_steps.items():
        if not isinstance(name, str) or not STEP_NAME_RE.match(name):
            raise ValueError(
                f"Invalid step name {name!r}: use lowercase letters, digits and underscores, starting with a "
                "letter."
            )
        if name in RESERVED_STEP_NAMES:
            raise ValueError(f"Step name {name!r} is reserved.")
        if not isinstance(raw, Mapping):
            raise ValueError(f"Step {name!r} must be a mapping with `scope` and `command` keys.")

        unknown_keys = sorted(set(raw) - STEP_KEYS)
        if unknown_keys:
            raise ValueError(
                f"Step {name!r} has unknown key(s) {unknown_keys}; allowed keys are {sorted(STEP_KEYS)}."
            )

        scope = raw.get("scope")
        if scope not in set(Scope):
            raise ValueError(
                f"Step {name!r} has invalid scope {scope!r}; expected one of {[s.value for s in Scope]}."
            )

        command = raw.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"Step {name!r} needs a non-empty `command` string.")

        needs = raw.get("needs") or []
        if isinstance(needs, str) or not isinstance(needs, Sequence):
            raise ValueError(f"Step {name!r} has invalid `needs`; expected a list of step names.")
        for need in needs:
            if need not in declared:
                raise ValueError(f"Step {name!r} needs {need!r}, which is not declared before it.")
            if scope == Scope.DATASET and declared[need].scope == Scope.TASK:
                raise ValueError(f"Dataset-scoped step {name!r} cannot need task-scoped step {need!r}.")
        if len(set(needs)) != len(needs):
            raise ValueError(f"Step {name!r} lists a step more than once in `needs`.")

        predict = raw.get("predict", False)
        if not isinstance(predict, bool):
            raise ValueError(f"Step {name!r} has invalid `predict`; expected true or false.")

        step = Step(name=name, scope=Scope(scope), command=command, needs=tuple(needs), predict=predict)
        steps.append(step)
        declared[name] = step

    predict_steps = [step for step in steps if step.predict]
    if len(predict_steps) != 1:
        raise ValueError(f"Exactly one step must set `predict: true`; found {len(predict_steps)}.")
    if predict_steps[0].scope != Scope.TASK:
        raise ValueError(f"The predict step {predict_steps[0].name!r} must be task-scoped.")
    if PREDICT_DIR_NAME in declared and not declared[PREDICT_DIR_NAME].predict:
        raise ValueError(f"Step name {PREDICT_DIR_NAME!r} is reserved for the directory of the predict step.")

    for step in steps:
        undefined = sorted(step.variables - step.allowed_variables)
        if undefined:
            raise ValueError(f"Step {step.name!r} uses undefined template variable(s) {undefined}.")

    profile = spec.get("profile")
    if profile is not None and profile not in set(Profile):
        raise ValueError(f"Unknown profile {profile!r}; expected one of {[p.value for p in Profile]}.")

    graph = StepGraph(steps=tuple(steps), profile=Profile(profile) if profile else None, schema_version=2)
    _validate_profile(graph)
    return graph


def _validate_profile(graph: StepGraph) -> None:
    profile = graph.profile
    if profile is None:
        return

    dataset_steps = [step.name for step in graph.steps if step.scope == Scope.DATASET]
    task_fit_steps = [step.name for step in graph.steps if step.scope == Scope.TASK and not step.predict]
    predict_step = graph.predict_step

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(f"Profile {profile.value!r} {message}")

    if profile in (Profile.FINETUNE, Profile.PROBE, Profile.ZERO_SHOT_DIRECT, Profile.ZERO_SHOT_MATERIALIZED):
        require(bool(dataset_steps), "needs at least one dataset-scoped (pre-training) step.")
    if profile in (Profile.SUPERVISED, Profile.FINETUNE, Profile.PROBE):
        require(bool(task_fit_steps), "needs at least one task-scoped training step before its predict step.")
    if profile in (Profile.ZERO_SHOT_DIRECT, Profile.PREDICT_ONLY):
        require(
            not task_fit_steps,
            f"must not have task-scoped steps other than its predict step; found {task_fit_steps}.",
        )
    if profile in (Profile.ZERO_SHOT_DIRECT, Profile.ZERO_SHOT_MATERIALIZED):
        require(
            "task_criteria_path" in predict_step.variables,
            "needs its predict step to use {task_criteria_path}.",
        )


def v1_to_step_graph(commands: Mapping[str, Any]) -> StepGraph:
    """Describes a version 1 `commands` block as a step graph.

    The step names are `<dataset_type>_<mode>`. `needs` mirrors how version 1 chains
    `model_initialization_dir` from one stage to the next. Commands keep their version 1 template variables
    (`{output_dir}`, `{model_initialization_dir}`), because version 1 models are still run by
    `model_commands`; this graph is for introspection (e.g., counting dataset-scoped steps) only.

    Examples:
        >>> graph = v1_to_step_graph({
        ...     "unsupervised": {"train": "pretrain"},
        ...     "supervised": {"train": "finetune", "predict": "predict"},
        ... })
        >>> [(s.name, s.scope.value, s.needs, s.predict) for s in graph.steps]
        [('unsupervised_train', 'dataset', (), False),
         ('supervised_train', 'task', ('unsupervised_train',), False),
         ('supervised_predict', 'task', ('supervised_train',), True)]
        >>> graph = v1_to_step_graph({"unsupervised": {"train": "pretrain"}, "supervised": {"train": None,
        ...                           "predict": "zero-shot"}})
        >>> [(s.name, s.needs) for s in graph.steps]
        [('unsupervised_train', ()), ('supervised_predict', ('unsupervised_train',))]
    """
    present: dict[str, Step] = {}
    for dataset_type, scope in (("unsupervised", Scope.DATASET), ("supervised", Scope.TASK)):
        stage_commands = commands.get(dataset_type) or {}
        for mode in ("train", "predict"):
            command = stage_commands.get(mode)
            if not command:
                continue
            name = f"{dataset_type}_{mode}"
            if name == "supervised_predict":
                previous = [n for n in ("supervised_train", "unsupervised_train") if n in present][:1]
            elif name == "unsupervised_train":
                previous = []
            else:
                previous = [n for n in ("unsupervised_train",) if n in present]
            present[name] = Step(
                name=name,
                scope=scope,
                command=command,
                needs=tuple(previous),
                predict=name == "supervised_predict",
            )
    return StepGraph(steps=tuple(present.values()), profile=None, schema_version=1)


def load_step_graph(spec: Mapping[str, Any]) -> StepGraph:
    """Returns the step graph of a `model.yaml`, of either schema version.

    Examples:
        >>> load_step_graph({"commands": {"supervised": {"predict": "p"}}}).schema_version
        1
        >>> load_step_graph({"schema_version": 3, "steps": {}})
        Traceback (most recent call last):
            ...
        ValueError: Unsupported model.yaml schema_version 3; supported versions are (1, 2).
        >>> load_step_graph({"schema_version": 2, "commands": {}, "steps": {}})
        Traceback (most recent call last):
            ...
        ValueError: A version 2 model.yaml uses `steps`, not `commands`.
        >>> load_step_graph({"profile": "probe", "commands": {}})
        Traceback (most recent call last):
            ...
        ValueError: `profile` and `steps` require `schema_version: 2`.
    """
    version = spec.get("schema_version", 1)
    if version not in SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported model.yaml schema_version {version}; supported versions are {SCHEMA_VERSIONS}."
        )
    if version == 1:
        if "steps" in spec or "profile" in spec:
            raise ValueError("`profile` and `steps` require `schema_version: 2`.")
        return v1_to_step_graph(spec.get("commands") or {})
    if "commands" in spec:
        raise ValueError("A version 2 model.yaml uses `steps`, not `commands`.")
    return parse_step_graph(spec)


def select_steps(
    graph: StepGraph,
    steps: Sequence[str] | None = None,
    dataset_type: str | None = None,
    mode: str | None = None,
    provided: Collection[str] = (),
) -> list[Step]:
    """Selects the steps a run executes: the requested ones plus every step they need.

    Steps are requested either by name (`steps`) or, as in version 1, by `dataset_type` and `mode`:
    `unsupervised` selects the dataset-scoped steps, `supervised` the task-scoped ones and `full` both;
    `train` selects the steps other than the predict step, `predict` the predict step, and `full` all of
    them. Steps in `provided` already have outputs (e.g., through `step_dirs`), so the steps they need are
    not added.

    Examples:
        >>> graph = parse_step_graph({"schema_version": 2, "steps": {
        ...     "pre": {"scope": "dataset", "command": "pre"},
        ...     "fit": {"scope": "task", "needs": ["pre"], "command": "fit"},
        ...     "pred": {"scope": "task", "needs": ["fit"], "predict": True, "command": "pred"},
        ... }})
        >>> def names(**kwargs):
        ...     return [step.name for step in select_steps(graph, **kwargs)]
        >>> names(dataset_type="unsupervised", mode="train")
        ['pre']
        >>> names(dataset_type="supervised", mode="predict")
        ['pre', 'fit', 'pred']
        >>> names(dataset_type="full", mode="full")
        ['pre', 'fit', 'pred']
        >>> names(steps=["fit"])
        ['pre', 'fit']
        >>> names(steps=["pred"], provided=["fit"])
        ['fit', 'pred']
        >>> names(dataset_type="unsupervised", mode="predict")
        Traceback (most recent call last):
            ...
        RuntimeError: Model has no steps for dataset_type=unsupervised and mode=predict.
        >>> names(dataset_type="supervised", mode="prediction")
        Traceback (most recent call last):
            ...
        ValueError: Invalid mode 'prediction'; expected one of ['train', 'predict', 'full'].
    """
    if steps:
        return graph.closure(list(steps), provided)

    scopes_by_type = {
        "unsupervised": {Scope.DATASET},
        "supervised": {Scope.TASK},
        "full": {Scope.DATASET, Scope.TASK},
    }
    if dataset_type not in scopes_by_type:
        raise ValueError(f"Invalid dataset_type {dataset_type!r}; expected one of {list(scopes_by_type)}.")
    mode_filters: dict[str, Callable[[Step], bool]] = {
        "train": lambda step: not step.predict,
        "predict": lambda step: step.predict,
        "full": lambda step: True,
    }
    if mode not in mode_filters:
        raise ValueError(f"Invalid mode {mode!r}; expected one of {list(mode_filters)}.")

    names = [
        step.name
        for step in graph.steps
        if step.scope in scopes_by_type[dataset_type] and mode_filters[mode](step)
    ]
    if not names:
        raise RuntimeError(f"Model has no steps for dataset_type={dataset_type} and mode={mode}.")
    return graph.closure(names, provided)


@dataclass(frozen=True)
class TaskInputs:
    """The task-specific inputs of a run."""

    name: str
    labels_dir: str | None = None
    task_criteria_path: str | None = None


@dataclass(frozen=True)
class PlannedStep:
    """A step ready to run (or, if `external`, already provided through `step_dirs`).

    Args:
        step: The step.
        task_name: The task it runs for, or None for dataset-scoped steps.
        run_dir: Where MEDS-DEV keeps the step's `cmd.sh` and `.done` marker.
        output_dir: The step's output directory, passed to it as `{step_dir}`.
        command: The formatted command, or None if the step is external.
        external: Whether the output was provided through `step_dirs`, so the step is not run.
    """

    step: Step
    task_name: str | None
    run_dir: Path | None
    output_dir: Path
    command: str | None
    external: bool = False


def predict_dir_name(split: str) -> str:
    """Returns the directory name of the predict step for a split.

    Examples:
        >>> predict_dir_name("held_out")
        'predict'
        >>> predict_dir_name("tuning")
        'predict.tuning'
    """
    return PREDICT_DIR_NAME if split == meds.held_out_split else f"{PREDICT_DIR_NAME}.{split}"


def _format(step: Step, variables: Mapping[str, Any]) -> str:
    missing = sorted(step.variables - set(variables))
    if missing:
        raise ValueError(
            f"Step {step.name!r} uses {', '.join('{' + m + '}' for m in missing)}, which is not set for "
            "this run. Set the corresponding meds-dev-model argument (e.g., predicates_path, task_name, "
            "labels_dir)."
        )
    return step.command.format(**variables)


def plan_steps(
    graph: StepGraph,
    selected: Sequence[Step],
    *,
    output_dir: Path | str,
    dataset_name: str | None,
    dataset_dir: Path | str,
    model_dir: Path | str,
    tasks: Sequence[TaskInputs] = (),
    split: str = meds.held_out_split,
    demo: bool = False,
    predicates_path: Path | str | None = None,
    shared_root: Path | str | None = None,
    step_dirs: Mapping[str, Path | str] | None = None,
) -> list[PlannedStep]:
    """Lays out the selected steps on disk and formats their commands.

    Dataset-scoped steps run once, under `<shared_root>/<step>/` (by default
    `<output_dir>/<dataset_name>/_shared/<step>/`). Task-scoped steps run for each task, under
    `<output_dir>/<dataset_name>/<task_name>/<step>/`; the predict step uses `predict/` (held-out split) or
    `predict.<split>/` instead of its name. Each step receives `<run dir>/output/` as `{step_dir}`.

    Examples:
        >>> graph = parse_step_graph({"schema_version": 2, "steps": {
        ...     "pre": {"scope": "dataset", "command": "pre {dataset_dir} {predicates_path} {step_dir}"},
        ...     "fit": {"scope": "task", "needs": ["pre"], "command": "fit {pre_dir} {labels_dir} {step_dir}"},
        ...     "pred": {"scope": "task", "needs": ["pre", "fit"], "predict": True,
        ...              "command": "pred {fit_dir} {task_criteria_path} {split} {step_dir}"},
        ... }})
        >>> plan = plan_steps(
        ...     graph, graph.steps, output_dir="/runs", dataset_name="MIMIC", dataset_dir="/data",
        ...     model_dir="/m", predicates_path="/p.yaml",
        ...     tasks=[TaskInputs("t1", "/labels/t1", "/c/t1.yaml"), TaskInputs("t2", "/labels/t2", "/c/t2.yaml")],
        ... )
        >>> for p in plan:
        ...     print(p.task_name, p.run_dir.as_posix(), "|", p.command)
        None /runs/MIMIC/_shared/pre | pre /data /p.yaml /runs/MIMIC/_shared/pre/output
        t1 /runs/MIMIC/t1/fit | fit /runs/MIMIC/_shared/pre/output /labels/t1 /runs/MIMIC/t1/fit/output
        t1 /runs/MIMIC/t1/predict | pred /runs/MIMIC/t1/fit/output /c/t1.yaml held_out /runs/MIMIC/t1/predict/output
        t2 /runs/MIMIC/t2/fit | fit /runs/MIMIC/_shared/pre/output /labels/t2 /runs/MIMIC/t2/fit/output
        t2 /runs/MIMIC/t2/predict | pred /runs/MIMIC/t2/fit/output /c/t2.yaml held_out /runs/MIMIC/t2/predict/output

    Outputs of earlier runs can be reused through `step_dirs` (those steps are not run) or `shared_root`:
        >>> plan = plan_steps(
        ...     graph, graph.steps, output_dir="/runs", dataset_name="MIMIC", dataset_dir="/data",
        ...     model_dir="/m", predicates_path="/p.yaml", tasks=[TaskInputs("t1", "/l", "/c.yaml")],
        ...     split="tuning", step_dirs={"pre": "/old/pre"},
        ... )
        >>> [(p.step.name, p.external, p.run_dir and p.run_dir.as_posix()) for p in plan]
        [('pre', True, None), ('fit', False, '/runs/MIMIC/t1/fit'), ('pred', False, '/runs/MIMIC/t1/predict.tuning')]
        >>> plan[1].command
        'fit /old/pre /l /runs/MIMIC/t1/fit/output'

    Missing inputs fail before anything runs:
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="MIMIC", dataset_dir="/data",
        ...            model_dir="/m", tasks=[TaskInputs("t1", "/l", "/c.yaml")])
        Traceback (most recent call last):
            ...
        ValueError: Step 'pre' uses {predicates_path}, which is not set for this run. Set the corresponding
        meds-dev-model argument (e.g., predicates_path, task_name, labels_dir).
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="MIMIC", dataset_dir="/data",
        ...            model_dir="/m", predicates_path="/p.yaml")
        Traceback (most recent call last):
            ...
        ValueError: This run includes task-scoped steps ['fit', 'pred'], so task_name (or tasks) must be set.
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name=None, dataset_dir="/data",
        ...            model_dir="/m")
        Traceback (most recent call last):
            ...
        ValueError: dataset_name must be set to run a version 2 model.
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="MIMIC", dataset_dir="/data",
        ...            model_dir="/m", step_dirs={"nope": "/x"})
        Traceback (most recent call last):
            ...
        ValueError: step_dirs names unknown step(s) ['nope']. Available steps: ['pre', 'fit', 'pred']
    """  # noqa: E501
    if not dataset_name:
        raise ValueError("dataset_name must be set to run a version 2 model.")

    step_dirs = dict(step_dirs or {})
    unknown = sorted(set(step_dirs) - set(graph.by_name))
    if unknown:
        raise ValueError(f"step_dirs names unknown step(s) {unknown}. Available steps: {list(graph.by_name)}")

    output_dir = Path(output_dir)
    dataset_root = output_dir / dataset_name
    shared_root = Path(shared_root) if shared_root else dataset_root / SHARED_DIR_NAME

    task_steps = [step for step in selected if step.scope == Scope.TASK]
    if task_steps and not tasks:
        raise ValueError(
            f"This run includes task-scoped steps {[s.name for s in task_steps]}, so task_name (or tasks) "
            "must be set."
        )
    task_step_dirs = [step.name for step in task_steps if step.name in step_dirs]
    if task_step_dirs and len(tasks) > 1:
        raise ValueError(
            f"step_dirs cannot provide task-scoped step(s) {task_step_dirs} when running several tasks."
        )

    base_variables: dict[str, Any] = {
        "dataset_dir": str(dataset_dir),
        "model_dir": str(model_dir),
        "demo": demo,
    }
    if predicates_path:
        base_variables["predicates_path"] = str(predicates_path)

    def plan_one(step: Step, run_dir: Path, outputs: dict[str, Path], task: TaskInputs | None) -> PlannedStep:
        if step.name in step_dirs:
            output = Path(step_dirs[step.name])
            outputs[step.name] = output
            return PlannedStep(step, task.name if task else None, None, output, None, external=True)

        output = run_dir / STEP_OUTPUT_SUBDIR
        variables = {**base_variables, "step_dir": str(output)}
        variables.update({f"{need}_dir": str(outputs[need]) for need in step.needs})
        if task is not None:
            if task.labels_dir:
                variables["labels_dir"] = str(task.labels_dir)
            if task.task_criteria_path:
                variables["task_criteria_path"] = str(task.task_criteria_path)
        if step.predict:
            variables["split"] = split
        outputs[step.name] = output
        return PlannedStep(step, task.name if task else None, run_dir, output, _format(step, variables))

    planned: list[PlannedStep] = []
    shared_outputs: dict[str, Path] = {}
    for step in selected:
        if step.scope == Scope.DATASET:
            planned.append(plan_one(step, shared_root / step.name, shared_outputs, None))

    if task_steps:
        for task in tasks:
            outputs = dict(shared_outputs)
            task_root = dataset_root / task.name
            for step in task_steps:
                dir_name = predict_dir_name(split) if step.predict else step.name
                planned.append(plan_one(step, task_root / dir_name, outputs, task))

    return planned


def resolve_overwrite(overwrite: str | None, do_overwrite: bool) -> Overwrite:
    """Resolves the overwrite policy; `do_overwrite=true` means `all` unless `overwrite` is set.

    Examples:
        >>> resolve_overwrite(None, False), resolve_overwrite(None, True), resolve_overwrite("task", True)
        (<Overwrite.NONE: 'none'>, <Overwrite.ALL: 'all'>, <Overwrite.TASK: 'task'>)
        >>> resolve_overwrite("some", False)
        Traceback (most recent call last):
            ...
        ValueError: Invalid overwrite 'some'; expected one of ['none', 'task', 'all'].
    """
    if overwrite is None:
        return Overwrite.ALL if do_overwrite else Overwrite.NONE
    if overwrite not in set(Overwrite):
        raise ValueError(f"Invalid overwrite {overwrite!r}; expected one of {[o.value for o in Overwrite]}.")
    return Overwrite(overwrite)


@contextlib.contextmanager
def step_lock(lock_fp: Path, timeout: float, poll_interval: float = 5.0) -> Iterator[None]:
    """Holds an exclusive lock file while a shared step runs, so concurrent runs do not run it twice.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     lock_fp = Path(d) / "pre.lock"
        ...     with step_lock(lock_fp, timeout=0):
        ...         held = lock_fp.exists()
        ...         try:
        ...             with step_lock(lock_fp, timeout=0, poll_interval=0):
        ...                 pass
        ...         except TimeoutError as e:
        ...             print("second run waits:", "is held by" in str(e))
        ...     print(held, lock_fp.exists())
        second run waits: True
        True False
    """
    lock_fp.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_fp, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                holder = lock_fp.read_text().strip() if lock_fp.exists() else "unknown"
                raise TimeoutError(
                    f"{lock_fp} is held by {holder}. If no other run is using this step (e.g., a previous "
                    "run crashed), delete the lock file and try again."
                ) from None
            logger.info(f"Waiting for {lock_fp} ...")
            time.sleep(poll_interval)
            continue
        with os.fdopen(fd, "w") as f:
            f.write(f"host={socket.gethostname()} pid={os.getpid()}\n")
        break
    try:
        yield
    finally:
        lock_fp.unlink(missing_ok=True)


def run_planned_steps(
    planned: Sequence[PlannedStep],
    runner: Callable[..., Any],
    *,
    env: dict[str, str] | None = None,
    overwrite: Overwrite = Overwrite.NONE,
    lock_timeout: float = 24 * 60 * 60,
) -> None:
    """Runs planned steps in order, skipping finished steps and locking shared ones.

    `runner(command, run_dir, env=env)` runs one command (in production, `MEDS_DEV.utils.run_in_env`, which
    skips the step if `run_dir/.done` exists and writes it on success).

    Examples:
        >>> import tempfile
        >>> graph = parse_step_graph({"schema_version": 2, "steps": {
        ...     "pre": {"scope": "dataset", "command": "pre"},
        ...     "pred": {"scope": "task", "needs": ["pre"], "predict": True, "command": "pred"},
        ... }})
        >>> def fake_runner(command, run_dir, env=None):
        ...     if (run_dir / ".done").exists():
        ...         return
        ...     print("run", command)
        ...     (run_dir / ".done").touch()
        >>> with tempfile.TemporaryDirectory() as d:
        ...     def plan(task):
        ...         return plan_steps(graph, graph.steps, output_dir=d, dataset_name="D", dataset_dir="/data",
        ...                           model_dir="/m", tasks=[TaskInputs(task)])
        ...     run_planned_steps(plan("t1"), fake_runner)
        ...     run_planned_steps(plan("t2"), fake_runner)  # the shared step is reused
        ...     run_planned_steps(plan("t1"), fake_runner, overwrite=Overwrite.TASK)
        ...     run_planned_steps(plan("t1"), fake_runner, overwrite=Overwrite.ALL)
        run pre
        run pred
        run pred
        run pred
        run pre
        run pred
    """
    for planned_step in planned:
        if planned_step.external:
            logger.info(f"Using existing output {planned_step.output_dir} for step {planned_step.step.name}.")
            continue

        run_dir = planned_step.run_dir
        is_shared = planned_step.step.scope == Scope.DATASET
        lock = (
            step_lock(run_dir.with_name(f"{run_dir.name}.lock"), timeout=lock_timeout)
            if is_shared
            else contextlib.nullcontext()
        )
        with lock:
            clear = overwrite == Overwrite.ALL or (overwrite == Overwrite.TASK and not is_shared)
            if clear and run_dir.exists():
                logger.info(f"Removing existing step directory: {run_dir}")
                shutil.rmtree(run_dir)
            planned_step.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Considering running step {planned_step.step.name}: {planned_step.command}")
            try:
                runner(planned_step.command, run_dir, env=env)
            except Exception as e:
                step_name = planned_step.step.name
                raise ValueError(f"Failed to run step {step_name}: {planned_step.command}") from e


__all__ = [
    "Overwrite",
    "PlannedStep",
    "Profile",
    "Scope",
    "Step",
    "StepGraph",
    "TaskInputs",
    "load_step_graph",
    "parse_step_graph",
    "plan_steps",
    "resolve_overwrite",
    "run_planned_steps",
    "select_steps",
    "step_lock",
    "v1_to_step_graph",
]
