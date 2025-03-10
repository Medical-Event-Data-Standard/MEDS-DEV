import dataclasses
from importlib.resources import files

from omegaconf import ListConfig, OmegaConf

from ..datasets import DATASETS
from ..utils import Metadata


@dataclasses.dataclass
class TaskMetadata(Metadata):
    """Task-specific metadata alterations.

    Args:
        supported_datasets: List of datasets that this task supports.

    Examples:
        >>> TaskMetadata(description="foo", contacts=[{"name": "bar"}]) # doctest: +NORMALIZE_WHITESPACE
        TaskMetadata(description='foo',
                     contacts=[Contact(name='bar', email=None, github_username=None)],
                    links=None,
                    supported_datasets=None)
        >>> TaskMetadata(
        ...     description="foo", contacts=[{"name": "bar"}], supported_datasets=[]
        ... ) # doctest: +NORMALIZE_WHITESPACE
        TaskMetadata(description='foo',
                     contacts=[Contact(name='bar', email=None, github_username=None)],
                     links=None,
                     supported_datasets=[])
        >>> TaskMetadata(
        ...     description="foo", contacts=[{"name": "bar"}], supported_datasets=["MIMIC-IV"]
        ... ) # doctest: +NORMALIZE_WHITESPACE
        TaskMetadata(description='foo',
                     contacts=[Contact(name='bar', email=None, github_username=None)],
                     links=None,
                     supported_datasets=['MIMIC-IV'])
        >>> TaskMetadata(description="foo", contacts=[{"name": "bar"}], supported_datasets=3)
        Traceback (most recent call last):
            ...
        ValueError: supported_datasets must be a list. Got <class 'int'>
        >>> TaskMetadata(description="foo", contacts=[{"name": "bar"}], supported_datasets=[3])
        Traceback (most recent call last):
            ...
        ValueError: supported_datasets[0] must be a string. Got <class 'int'>
        >>> TaskMetadata(description="foo", contacts=[{"name": "bar"}], supported_datasets=["_not_real"])
        Traceback (most recent call last):
            ...
        ValueError: supported_datasets[0] = '_not_real' is not a MEDS-DEV dataset. Valid datasets are: ...
    """

    supported_datasets: list[str] | None = None

    def __post_init__(self):
        super().__post_init__()

        if self.supported_datasets is None:
            return
        if not isinstance(self.supported_datasets, (list, ListConfig)):
            raise ValueError(f"supported_datasets must be a list. Got {type(self.supported_datasets)}")
        for i, dataset in enumerate(self.supported_datasets):
            if not isinstance(dataset, str):
                raise ValueError(f"supported_datasets[{i}] must be a string. Got {type(dataset)}")
            if dataset not in DATASETS:
                raise ValueError(
                    f"supported_datasets[{i}] = '{dataset}' is not a MEDS-DEV dataset. "
                    f"Valid datasets are: {', '.join(DATASETS.keys())}"
                )


task_files = files("MEDS_DEV.tasks")
CFG_YAML = files("MEDS_DEV.configs") / "_extract_task.yaml"
ACES_CFG_YAML = files("MEDS_DEV.configs") / "_ACES_MD.yaml"

TASKS = {}
for path in task_files.glob("**/*.yaml"):
    task = path.relative_to(task_files).with_suffix("").as_posix()

    cfg = OmegaConf.load(path)
    if cfg.get("metadata", None):
        metadata = TaskMetadata(**cfg.get("metadata"))
    else:
        metadata = None

    TASKS[task] = {
        "criteria_fp": path,
        "metadata": metadata,
    }

__all__ = ["TASKS", "CFG_YAML", "ACES_CFG_YAML"]
