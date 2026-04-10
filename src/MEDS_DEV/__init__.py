from importlib.metadata import PackageNotFoundError, version

from .datasets import DATASETS
from .models import MODELS
from .tasks import TASKS

__all__ = ["DATASETS", "MODELS", "TASKS"]

__package_name__ = "MEDS_DEV"
try:
    __version__ = version(__package_name__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
