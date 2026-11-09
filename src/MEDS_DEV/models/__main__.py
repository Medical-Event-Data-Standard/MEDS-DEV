import logging
from pathlib import Path

import hydra
import meds
from omegaconf import DictConfig, OmegaConf

from ..utils import clear_output_dir, run_in_env, temp_env
from . import CFG_YAML, MODELS, get_model, model_commands, task_criteria_path
from .steps import (
    SHARED_DIR_NAME,
    PlannedStep,
    StepGraph,
    TaskInputs,
    plan_steps,
    resolve_overwrite,
    run_planned_steps,
    select_steps,
)

logger = logging.getLogger(__name__)


def task_inputs(cfg: DictConfig) -> list[TaskInputs]:
    """Returns the tasks of a version 2 run: `tasks` (with `labels_root`), or the single `task_name`."""
    tasks = cfg.get("tasks", None)
    if tasks:
        if cfg.get("task_criteria_path", None):
            raise ValueError(
                "task_criteria_path cannot be combined with tasks; each task uses its registered criteria "
                "file."
            )
        labels_root = cfg.get("labels_root", None)
        if not labels_root:
            raise ValueError(
                "labels_root must be set when tasks is set; task labels are read from labels_root/<task>."
            )
        return [
            TaskInputs(
                name=str(task),
                labels_dir=str(Path(labels_root) / str(task)),
                task_criteria_path=task_criteria_path(str(task)),
            )
            for task in tasks
        ]

    task_name = cfg.get("task_name", None)
    if not task_name:
        return []
    labels_dir = cfg.get("labels_dir", None)
    return [
        TaskInputs(
            name=str(task_name),
            labels_dir=str(labels_dir) if labels_dir else None,
            task_criteria_path=task_criteria_path(str(task_name), cfg.get("task_criteria_path", None)),
        )
    ]


def plan_from_cfg(cfg: DictConfig, graph: StepGraph, model_dir: Path) -> list[PlannedStep]:
    """Plans a version 2 model run from the `meds-dev-model` configuration."""
    step_dirs = cfg.get("step_dirs", None) or {}
    if isinstance(step_dirs, DictConfig):
        step_dirs = OmegaConf.to_container(step_dirs, resolve=True)

    requested_steps = cfg.get("steps", None)
    selected = select_steps(
        graph,
        steps=list(requested_steps) if requested_steps else None,
        dataset_type=cfg.get("dataset_type", None),
        mode=cfg.get("mode", None),
        provided=set(step_dirs),
    )

    dataset_name = cfg.get("dataset_name", None)
    shared_root = None
    if cfg.get("model_initialization_dir", None) and dataset_name:
        # Reuse the shared (dataset-scoped) steps of an earlier run, whose output_dir was
        # model_initialization_dir.
        shared_root = Path(cfg.model_initialization_dir) / dataset_name / SHARED_DIR_NAME

    return plan_steps(
        graph,
        selected,
        output_dir=Path(cfg.output_dir),
        dataset_name=dataset_name,
        dataset_dir=cfg.dataset_dir,
        model_dir=model_dir,
        tasks=task_inputs(cfg),
        split=cfg.get("split", None) or meds.held_out_split,
        demo=cfg.get("demo", False),
        predicates_path=cfg.get("predicates_path", None),
        shared_root=shared_root,
        step_dirs=step_dirs,
    )


@hydra.main(version_base=None, config_path=str(CFG_YAML.parent), config_name=CFG_YAML.stem)
def main(cfg: DictConfig):
    if cfg.model not in MODELS:
        raise ValueError(f"Model {cfg.model} not currently configured. Available models: {MODELS.keys()}")

    model = get_model(cfg.model)
    model_dir = model["model_dir"]
    requirements = model["requirements"]
    output_dir = Path(cfg.output_dir)

    if model["schema_version"] >= 2:
        # Plan (and validate) every step before creating environments or running anything.
        planned = plan_from_cfg(cfg, model["step_graph"], model_dir)
        overwrite = resolve_overwrite(cfg.get("overwrite", None), cfg.get("do_overwrite", False))
        output_dir.mkdir(parents=True, exist_ok=True)
        with temp_env(cfg, requirements) as (_temp_dir, env):
            run_planned_steps(
                planned,
                run_in_env,
                env=env,
                overwrite=overwrite,
                lock_timeout=cfg.get("lock_timeout", 24 * 60 * 60),
            )
        logger.info(f"Model {cfg.model} finished successfully.")
        return

    commands = model["commands"]

    if cfg.get("do_overwrite", False) and output_dir.exists():  # pragma: no cover
        logger.info(f"Clearing existing output directory: {output_dir}")
        clear_output_dir(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    with temp_env(cfg, requirements) as (_temp_dir, env):
        for cmd, out_dir in model_commands(cfg, commands, model_dir):
            logger.info(f"Considering running model command: {cmd}")
            try:
                run_in_env(cmd, out_dir, env=env, do_overwrite=cfg.do_overwrite)
            except Exception as e:  # pragma: no cover
                raise ValueError(f"Failed to run {cfg.model} command {cmd}") from e

    logger.info(f"Model {cfg.model} finished successfully.")
