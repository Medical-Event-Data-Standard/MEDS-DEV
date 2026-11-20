from importlib.resources import files
from pathlib import Path

from omegaconf import OmegaConf

from ..tasks import TASKS
from ..utils import Metadata
from .steps import parse_step_graph

model_files = files("MEDS_DEV.models")
CFG_YAML = files("MEDS_DEV.configs") / "_run_model.yaml"

MODELS = {}


def load_model_yaml(model_yaml: Path, model_name: str) -> dict:
    """Loads and validates a `model.yaml` into a registry entry.

    The entry holds the file's contents, with `metadata` parsed and the validated `step_graph` added (see
    `MEDS_DEV.models.steps`). Invalid files fail here, i.e., when the registry is loaded.
    """
    entry = OmegaConf.to_object(OmegaConf.load(model_yaml))
    try:
        entry["step_graph"] = parse_step_graph(entry)
    except ValueError as e:
        raise ValueError(f"Invalid model.yaml for model {model_name} ({model_yaml}): {e}") from e
    entry["metadata"] = Metadata(**entry["metadata"])
    return entry


for path in model_files.rglob("*/model.yaml"):
    model_name = path.relative_to(model_files).parent.with_suffix("").as_posix()
    MODELS[model_name] = load_model_yaml(path, model_name)
    requirements_path = path.parent / "requirements.txt"
    MODELS[model_name]["requirements"] = requirements_path if requirements_path.exists() else None
    MODELS[model_name]["model_dir"] = path.parent


def task_criteria_path(task_name: str | None, explicit_path: str | Path | None = None) -> str | None:
    """Returns a task's ACES criteria file: `explicit_path` if set, else the registered file of `task_name`.

    This is the value of the `{task_criteria_path}` template variable, for models that predict a task from
    its definition rather than from its labels (e.g., zero-shot models). It pairs with `predicates_path`
    exactly as in `meds-dev-task`.

    Examples:
        >>> task_criteria_path("not/a/task", "local/criteria.yaml")
        'local/criteria.yaml'
        >>> criteria_fp = task_criteria_path("mortality/in_icu/first_24h")
        >>> Path(criteria_fp).as_posix().endswith("tasks/mortality/in_icu/first_24h.yaml")
        True
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


__all__ = ["CFG_YAML", "MODELS", "load_model_yaml", "task_criteria_path"]
