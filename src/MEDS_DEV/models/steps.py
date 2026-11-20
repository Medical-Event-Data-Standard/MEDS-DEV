"""Model steps: the `model.yaml` schema, and how its steps are laid out and run.

A `model.yaml` names a `profile` and gives one shell command per step of that profile:

```yaml
metadata: {...}
profile: finetune
steps:
  preprocess_data: my-model preprocess_data input={dataset_dir} output={step_dir}
  pretrain: my-model pretrain data={preprocess_data_dir} output={step_dir}
  train_finetune: my-model train_finetune encoder={pretrain_dir} labels={labels_dir} output={step_dir}
  predict_finetune: my-model predict_finetune model={train_finetune_dir} split={split} output={step_dir}
```

The profiles and their steps are those of the `meds-algorithm` package (see `PROFILE_STEPS`), so everything
else about a step follows from its name:

- its scope: `preprocess_data` and `pretrain` are task-independent, so they run once per dataset and are
  shared by every task; the other steps run once per task;
- its order, and which step holds the predictions to evaluate (the last one);
- the earlier steps it needs: those whose output directory (`{<step>_dir}`) its command uses.

The earlier format (a `commands` block with `unsupervised`/`supervised` x `train`/`predict` slots) is no
longer supported; `parse_step_graph` rejects it with a pointer to the README.
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

#: The steps of each profile, in order. The last step of a profile is its predict step. This mirrors the
#: profile classes of `meds_algorithm.algorithms`, which are the authority for these lifecycles.
PROFILE_STEPS: dict[str, tuple[str, ...]] = {
    "supervised": ("preprocess_data", "train_supervised", "predict_supervised"),
    "finetune": ("preprocess_data", "pretrain", "train_finetune", "predict_finetune"),
    "probe": ("preprocess_data", "pretrain", "infer_embeddings", "train_probe", "predict_probe"),
    "zero_shot_direct": ("preprocess_data", "pretrain", "predict_zero_shot_direct"),
    "zero_shot_materialized": (
        "preprocess_data",
        "pretrain",
        "infer_trajectories",
        "predict_zero_shot_materialized",
    ),
    "predict_only": ("preprocess_data", "predict_only"),
}
#: The task-independent steps: they receive no labels, run once per dataset and are shared by every task.
DATASET_STEPS = frozenset({"preprocess_data", "pretrain"})
#: A model without task-independent preprocessing may leave this step out. Every other step is required.
OPTIONAL_STEPS = frozenset({"preprocess_data"})

#: Directory (under `<output_dir>/<dataset_name>/`) holding the dataset-scoped steps shared by all tasks.
SHARED_DIR_NAME = "_shared"
#: Directory (under a task's directory) holding the predict step's output for the held-out split.
PREDICT_DIR_NAME = "predict"
#: Subdirectory of a step's run directory that is passed to the step as `{step_dir}`. The run directory
#: itself holds MEDS-DEV's own files (`cmd.sh`, `.done`), so they never mix with the step's artifacts.
STEP_OUTPUT_SUBDIR = "output"

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


class Overwrite(StrEnum):
    """Which step directories a run clears before running its steps.

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

    Args:
        name: The step's name, one of its profile's steps.
        scope: Whether it runs once per dataset or once per task.
        command: The shell command, with template variables.
        needs: The earlier steps whose output directories the command uses.
        predict: Whether its output holds the predictions to evaluate.
    """

    name: str
    scope: Scope
    command: str
    needs: tuple[str, ...] = ()
    predict: bool = False

    @property
    def variables(self) -> set[str]:
        return command_variables(self.command)


@dataclass(frozen=True)
class StepGraph:
    """The steps of a model, in the order of its profile (which is always a valid execution order).

    Examples:
        >>> graph = parse_step_graph({"profile": "supervised", "steps": {
        ...     "preprocess_data": "pre {dataset_dir} {step_dir}",
        ...     "train_supervised": "fit {preprocess_data_dir} {labels_dir} {step_dir}",
        ...     "predict_supervised": "pred {train_supervised_dir} {labels_dir} {split} {step_dir}",
        ... }})
        >>> [(s.name, s.scope.value, s.needs) for s in graph.steps]
        [('preprocess_data', 'dataset', ()),
         ('train_supervised', 'task', ('preprocess_data',)),
         ('predict_supervised', 'task', ('train_supervised',))]
        >>> graph.predict_step.name
        'predict_supervised'
        >>> [s.name for s in graph.closure(["train_supervised"])]
        ['preprocess_data', 'train_supervised']
        >>> [s.name for s in graph.closure(["predict_supervised"], provided={"train_supervised"})]
        ['train_supervised', 'predict_supervised']
        >>> [s.name for s in graph.closure()]
        ['preprocess_data', 'train_supervised', 'predict_supervised']
        >>> graph.closure(["fit"])
        Traceback (most recent call last):
            ...
        ValueError: Unknown step(s) ['fit']. Available steps: ['preprocess_data', 'train_supervised',
        'predict_supervised']
    """

    steps: tuple[Step, ...]
    profile: str

    @property
    def by_name(self) -> dict[str, Step]:
        return {step.name: step for step in self.steps}

    @property
    def predict_step(self) -> Step:
        return self.steps[-1]

    def closure(self, names: Sequence[str] | None = None, provided: Collection[str] = ()) -> list[Step]:
        """Returns the named steps (default: all) and every step they need, in order.

        The needs of `provided` steps (whose outputs already exist, e.g., through `step_dirs`) are not
        followed.
        """
        by_name = self.by_name
        if not names:
            names = list(by_name)
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
    """Parses and validates the `profile` and `steps` of a `model.yaml`.

    Examples:
        >>> def check(profile, steps):
        ...     try:
        ...         parse_step_graph({"profile": profile, "steps": steps})
        ...     except ValueError as e:
        ...         print(e)
        >>> check("predict_only", {"predict_only": "p {labels_dir} {split} {step_dir}"})

    The steps are those of the profile: no others, and none missing except `preprocess_data`.
        >>> check("few_shot", {"predict_only": "p"})
        A model.yaml needs a `profile`, one of ['supervised', 'finetune', 'probe', 'zero_shot_direct',
        'zero_shot_materialized', 'predict_only']; got 'few_shot'.
        >>> check("supervised", {})
        A model.yaml needs a non-empty `steps` mapping.
        >>> check("supervised", {"fit": "f", "predict_supervised": "p"})
        Step(s) ['fit'] are not part of profile 'supervised', whose steps are ['preprocess_data',
        'train_supervised', 'predict_supervised'].
        >>> check("finetune", {"pretrain": "p", "predict_finetune": "p"})
        Profile 'finetune' also needs step(s) ['train_finetune'].
        >>> check("predict_only", {"predict_only": "  "})
        Step 'predict_only' needs a non-empty command string.

    A command can only use the variables of its step: the output of an earlier step, the task's inputs in
    task-scoped steps, and the split in the predict step.
        >>> check("finetune", {"pretrain": "p {labels_dir}", "train_finetune": "t", "predict_finetune": "p"})
        Step 'pretrain' uses undefined template variable(s) ['labels_dir'].
        >>> check("supervised", {"train_supervised": "t {predict_supervised_dir}", "predict_supervised": "p"})
        Step 'train_supervised' uses undefined template variable(s) ['predict_supervised_dir'].
        >>> check("supervised", {"train_supervised": "t {split}", "predict_supervised": "p"})
        Step 'train_supervised' uses undefined template variable(s) ['split'].

    Zero-shot models predict a task from its definition:
        >>> check("zero_shot_direct", {"pretrain": "p", "predict_zero_shot_direct": "p {pretrain_dir}"})
        Profile 'zero_shot_direct' needs its predict step to use {task_criteria_path}.

    The earlier format is rejected:
        >>> parse_step_graph({"commands": {"supervised": {"predict": "p {output_dir}"}}})
        Traceback (most recent call last):
            ...
        ValueError: A model.yaml lists `steps`; the `commands` block is no longer supported. See "Adding a
        model" in the README to migrate.
    """
    if "commands" in spec:
        raise ValueError(
            'A model.yaml lists `steps`; the `commands` block is no longer supported. See "Adding a '
            'model" in the README to migrate.'
        )
    profile = spec.get("profile")
    if profile not in PROFILE_STEPS:
        raise ValueError(f"A model.yaml needs a `profile`, one of {list(PROFILE_STEPS)}; got {profile!r}.")
    lifecycle = PROFILE_STEPS[profile]

    commands = spec.get("steps")
    if not isinstance(commands, Mapping) or not commands:
        raise ValueError("A model.yaml needs a non-empty `steps` mapping.")
    unknown = [name for name in commands if name not in lifecycle]
    if unknown:
        raise ValueError(
            f"Step(s) {unknown} are not part of profile {profile!r}, whose steps are {list(lifecycle)}."
        )
    missing = [name for name in lifecycle if name not in commands and name not in OPTIONAL_STEPS]
    if missing:
        raise ValueError(f"Profile {profile!r} also needs step(s) {missing}.")

    steps: list[Step] = []
    for name in lifecycle:
        if name not in commands:
            continue
        command = commands[name]
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"Step {name!r} needs a non-empty command string.")

        scope = Scope.DATASET if name in DATASET_STEPS else Scope.TASK
        predict = name == lifecycle[-1]
        variables = command_variables(command)
        needs = tuple(earlier.name for earlier in steps if f"{earlier.name}_dir" in variables)

        allowed = COMMON_VARIABLES | {f"{need}_dir" for need in needs}
        if scope == Scope.TASK:
            allowed |= TASK_VARIABLES
        if predict:
            allowed |= PREDICT_VARIABLES
        undefined = sorted(variables - allowed)
        if undefined:
            raise ValueError(f"Step {name!r} uses undefined template variable(s) {undefined}.")

        steps.append(Step(name=name, scope=scope, command=command, needs=needs, predict=predict))

    if profile.startswith("zero_shot_") and "task_criteria_path" not in steps[-1].variables:
        raise ValueError(f"Profile {profile!r} needs its predict step to use {{task_criteria_path}}.")

    return StepGraph(steps=tuple(steps), profile=profile)


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
    """

    step: Step
    task_name: str | None
    run_dir: Path | None
    output_dir: Path
    command: str | None

    @property
    def external(self) -> bool:
        """Whether the output was provided through `step_dirs`, so the step is not run."""
        return self.command is None


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
        >>> graph = parse_step_graph({"profile": "supervised", "steps": {
        ...     "preprocess_data": "pre {dataset_dir} {predicates_path} {step_dir}",
        ...     "train_supervised": "fit {preprocess_data_dir} {labels_dir} {step_dir}",
        ...     "predict_supervised": "pred {train_supervised_dir} {task_criteria_path} {split} {step_dir}",
        ... }})
        >>> plan = plan_steps(
        ...     graph, graph.steps, output_dir="/runs", dataset_name="D", dataset_dir="/data",
        ...     model_dir="/m", predicates_path="/p.yaml",
        ...     tasks=[TaskInputs("t1", "/labels/t1", "/c/t1.yaml"), TaskInputs("t2", "/labels/t2", "/c/t2.yaml")],
        ... )
        >>> for p in plan:
        ...     print(p.task_name, p.run_dir.as_posix(), "|", p.command)
        None /runs/D/_shared/preprocess_data | pre /data /p.yaml /runs/D/_shared/preprocess_data/output
        t1 /runs/D/t1/train_supervised | fit /runs/D/_shared/preprocess_data/output /labels/t1 /runs/D/t1/train_supervised/output
        t1 /runs/D/t1/predict | pred /runs/D/t1/train_supervised/output /c/t1.yaml held_out /runs/D/t1/predict/output
        t2 /runs/D/t2/train_supervised | fit /runs/D/_shared/preprocess_data/output /labels/t2 /runs/D/t2/train_supervised/output
        t2 /runs/D/t2/predict | pred /runs/D/t2/train_supervised/output /c/t2.yaml held_out /runs/D/t2/predict/output

    Outputs of earlier runs can be reused through `step_dirs` (those steps are not run) or `shared_root`:
        >>> plan = plan_steps(
        ...     graph, graph.steps, output_dir="/runs", dataset_name="D", dataset_dir="/data",
        ...     model_dir="/m", predicates_path="/p.yaml", tasks=[TaskInputs("t1", "/l", "/c.yaml")],
        ...     split="tuning", step_dirs={"preprocess_data": "/old/pre"},
        ... )
        >>> [(p.step.name, p.external, p.run_dir and p.run_dir.as_posix()) for p in plan]
        [('preprocess_data', True, None),
         ('train_supervised', False, '/runs/D/t1/train_supervised'),
         ('predict_supervised', False, '/runs/D/t1/predict.tuning')]
        >>> plan[1].command
        'fit /old/pre /l /runs/D/t1/train_supervised/output'

    Missing inputs fail before anything runs:
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="D", dataset_dir="/data",
        ...            model_dir="/m", tasks=[TaskInputs("t1", "/l", "/c.yaml")])
        Traceback (most recent call last):
            ...
        ValueError: Step 'preprocess_data' uses {predicates_path}, which is not set for this run. Set the
        corresponding meds-dev-model argument (e.g., predicates_path, task_name, labels_dir).
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="D", dataset_dir="/data",
        ...            model_dir="/m", predicates_path="/p.yaml")
        Traceback (most recent call last):
            ...
        ValueError: This run includes task-scoped steps ['train_supervised', 'predict_supervised'], so
        task_name (or tasks) must be set.
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name=None, dataset_dir="/data",
        ...            model_dir="/m")
        Traceback (most recent call last):
            ...
        ValueError: dataset_name must be set to run a model.
        >>> plan_steps(graph, graph.steps, output_dir="/runs", dataset_name="D", dataset_dir="/data",
        ...            model_dir="/m", step_dirs={"nope": "/x"})
        Traceback (most recent call last):
            ...
        ValueError: step_dirs names unknown step(s) ['nope']. Available steps: ['preprocess_data',
        'train_supervised', 'predict_supervised']
    """  # noqa: E501
    if not dataset_name:
        raise ValueError("dataset_name must be set to run a model.")

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
            return PlannedStep(step, task.name if task else None, None, output, None)

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
        >>> graph = parse_step_graph({"profile": "predict_only", "steps": {
        ...     "preprocess_data": "pre", "predict_only": "pred",
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
    "PROFILE_STEPS",
    "Overwrite",
    "PlannedStep",
    "Scope",
    "Step",
    "StepGraph",
    "TaskInputs",
    "parse_step_graph",
    "plan_steps",
    "resolve_overwrite",
    "run_planned_steps",
    "step_lock",
]
