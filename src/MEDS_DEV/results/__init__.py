import dataclasses
import datetime
import json
import logging
from importlib.resources import files
from pathlib import Path
from typing import Any

from .. import __version__
from ..datasets import DATASETS
from ..models import MODELS
from ..tasks import TASKS

logger = logging.getLogger(__name__)


def _is_future(dt: datetime.datetime) -> bool:
    """Checks if a datetime (either aware or naive and assumed to be UTC) is in the future.

    Args:
        dt: The datetime to check. If naive, it is assumed to be UTC and a warning will be logged.

    Returns:
        True if the datetime is in the future, False otherwise.

    Examples:
        >>> _is_future(datetime.datetime(2021, 9, 1, 12, 0, 0))
        False
        >>> _is_future(datetime.datetime(2021, 9, 1, 12, 0, 0, tzinfo=datetime.timezone.utc))
        False
        >>> _is_future(datetime.datetime.now() + datetime.timedelta(days=1))
        True
        >>> _is_future(datetime.datetime.today() + datetime.timedelta(days=1))
        True
    """

    is_aware = (dt.tzinfo is not None) and (dt.tzinfo.utcoffset(dt) is not None)
    if is_aware:
        return dt > datetime.datetime.now(dt.tzinfo)
    else:
        logger.warning("Naive datetime detected. Assuming UTC.")
        return dt > datetime.datetime.utcnow()


@dataclasses.dataclass
class Result:
    """The schema for a MEDS-DEV experimental result.

    Args:
        dataset: The name of the dataset.
        task: The name of the task.
        model: The name of the model.
        timestamp: The time the experiment was run.
        result: The result of the experiment.
        version: The version of the MEDS-DEV package used to generate the result. If this is set to the
            current package version, the dataset, task, and model names will be validated to ensure they are
            supported by the current version of the package.

    Examples:
        >>> result = Result(
        ...     dataset="MIMIC-IV", task="mortality/in_icu/first_24h", model="random_predictor",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5}, version='foo'
        ... )
        >>> result.dataset
        'MIMIC-IV'
        >>> result.task
        'mortality/in_icu/first_24h'
        >>> result.model
        'random_predictor'
        >>> result.timestamp
        datetime.datetime(2021, 9, 1, 12, 0)
        >>> result.result
        {'accuracy': 0.5}
        >>> result.version
        'foo'

        The result can also be written to and read from a JSON file; directories will be created as needed:

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     fp = Path(d) / "foo" / "result.json"
        ...     result.to_json(fp)
        ...     result2 = Result.from_json(fp)
        >>> result == result2
        True

        Reading from an erroneous or nonexistent file will raise an error:

        >>> with tempfile.TemporaryDirectory() as d:
        ...     Result.from_json(Path(d) / "nonexistent.json")
        Traceback (most recent call last):
            ...
        FileNotFoundError: /tmp/tmp.../nonexistent.json does not exist.
        >>> with tempfile.TemporaryDirectory() as d:
        ...     Result.from_json(Path(d))
        Traceback (most recent call last):
            ...
        ValueError: /tmp/tmp... is not a file.
        >>> with tempfile.NamedTemporaryFile(suffix=".json") as fp:
        ...     fp.write(b"not JSON")
        ...     Result.from_json(Path(fp.name))
        Traceback (most recent call last):
            ...
        ValueError: Could not read result from ...

        You can overwrite an existing file if and only if you set `do_overwrite=True`:

        >>> with tempfile.NamedTemporaryFile(suffix=".json") as fp:
        ...     result.to_json(Path(fp.name), do_overwrite=True)
        ...     result2 = Result.from_json(Path(fp.name))
        >>> result == result2
        True
        >>> with tempfile.NamedTemporaryFile(suffix=".json") as fp:
        ...     result.to_json(Path(fp.name), do_overwrite=False)
        Traceback (most recent call last):
            ...
        FileExistsError: /tmp/tmp...json already exists. Set do_overwrite=True to overwrite.

        Though attempting to overwrite a directory will always raise an error:

        >>> with tempfile.TemporaryDirectory() as d:
        ...     result.to_json(Path(d), do_overwrite=True)
        Traceback (most recent call last):
            ...
        ValueError: /tmp/tmp... is not a file.

        If you don't specify a version, the current package version will be used:

        >>> from MEDS_DEV import __version__ as MEDS_DEV_version
        >>> result = Result(
        ...     dataset="MIMIC-IV", task="mortality/in_icu/first_24h", model="random_predictor",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5}
        ... )
        >>> result.version == MEDS_DEV_version
        True

        If a current version is used, the result will be validated to ensure the dataset, task, and model
        are supported by the current version of the package:

        >>> result = Result(
        ...     dataset="not supported", task="mortality/in_icu/first_24h", model="random_predictor",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5}, version='foo'
        ... )
        >>> result.dataset
        'not supported'
        >>> result.version
        'foo'
        >>> Result(
        ...     dataset="not supported", task="mortality/in_icu/first_24h", model="random_predictor",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5}
        ... )
        Traceback (most recent call last):
            ...
        ValueError: Unknown dataset: not supported. For a current version, options are: ...
        >>> Result(
        ...     dataset="MIMIC-IV", task="not supported", model="random_predictor",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5}
        ... )
        Traceback (most recent call last):
            ...
        ValueError: Unknown task: not supported. For a current version, options are: ...
        >>> Result(
        ...     dataset="MIMIC-IV", task="mortality/in_icu/first_24h", model="not supported",
        ...     timestamp=datetime.datetime(2021, 9, 1, 12, 0, 0), result={'accuracy': 0.5},
        ...     version=MEDS_DEV_version
        ... )
        Traceback (most recent call last):
            ...
        ValueError: Unknown model: not supported. For a current version, options are: ...

        Version-independent results will still be validated for core typing, json serializability, and other
        expectations:

        >>> now = datetime.datetime.now()
        >>> Result(dataset=1, task="t", model="m", timestamp=now, result={}, version="v")
        Traceback (most recent call last):
            ...
        TypeError: dataset must be a string, not <class 'int'>
        >>> Result(dataset="d", task=1, model="m", timestamp=now, result={}, version="v")
        Traceback (most recent call last):
            ...
        TypeError: task must be a string, not <class 'int'>
        >>> Result(dataset="d", task="t", model=1, timestamp=now, result={}, version="v")
        Traceback (most recent call last):
            ...
        TypeError: model must be a string, not <class 'int'>
        >>> Result(dataset="d", task="t", model="m", timestamp="baz", result={}, version="v")
        Traceback (most recent call last):
            ...
        TypeError: timestamp must be a datetime object, not <class 'str'>
        >>> Result(dataset="d", task="t", model="m", timestamp=now, result=1, version="v")
        Traceback (most recent call last):
            ...
        TypeError: result must be a dictionary, not <class 'int'>
        >>> Result(dataset="d", task="t", model="m", timestamp=now, result={}, version=1)
        Traceback (most recent call last):
            ...
        TypeError: version must be a string, not <class 'int'>
        >>> future_date = now + datetime.timedelta(days=1)
        >>> Result(dataset="d", task="t", model="m", timestamp=future_date, result={}, version="v")
        Traceback (most recent call last):
            ...
        ValueError: timestamp must be in the past, not ...
        >>> non_serializable = {"foo": lambda x: x}
        >>> Result(
        ...     dataset="d", task="t", model="m", timestamp=now, result=non_serializable,
        ...     version="v"
        ... )
        Traceback (most recent call last):
            ...
        ValueError: Result must be JSON serializable! Got ...
    """

    dataset: str
    task: str
    model: str
    timestamp: datetime.datetime
    result: dict[str, Any]

    version: str = __version__

    def __post_init__(self):
        if not isinstance(self.timestamp, datetime.datetime):
            raise TypeError(f"timestamp must be a datetime object, not {type(self.timestamp)}")
        if not isinstance(self.result, dict):
            raise TypeError(f"result must be a dictionary, not {type(self.result)}")
        for k in ("dataset", "task", "model", "version"):
            if not isinstance(getattr(self, k), str):
                raise TypeError(f"{k} must be a string, not {type(getattr(self, k))}")

        if _is_future(self.timestamp):
            raise ValueError(f"timestamp must be in the past, not {self.timestamp}")

        try:
            json.dumps(self.result)
        except Exception as e:
            raise ValueError(f"Result must be JSON serializable! Got {self.result}") from e

        if self.version == __version__:
            if self.dataset not in DATASETS:
                raise ValueError(
                    f"Unknown dataset: {self.dataset}. For a current version, options are: {list(DATASETS)}"
                )
            if self.task not in TASKS:
                raise ValueError(
                    f"Unknown task: {self.task}. For a current version, options are: {list(TASKS)}"
                )
            if self.model not in MODELS:
                raise ValueError(
                    f"Unknown model: {self.model}. For a current version, options are: {list(MODELS)}"
                )
        else:
            logger.warning(
                f"Result version mismatch: {self.version} != {__version__}.\n"
                "Assuming this is a historical result and not validating dataset, task, and model names."
            )

    def to_json(self, fp: Path, do_overwrite: bool = False):
        """Write the result to a JSON file."""

        if fp.exists():
            if not fp.is_file():
                raise ValueError(f"{fp} is not a file.")
            if not do_overwrite:
                raise FileExistsError(f"{fp} already exists. Set do_overwrite=True to overwrite.")
            fp.unlink()
        else:
            fp.parent.mkdir(parents=True, exist_ok=True)

        as_dict = dataclasses.asdict(self)
        as_dict["timestamp"] = self.timestamp.isoformat()

        try:
            fp.write_text(json.dumps(as_dict))
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Could not write result to {fp}") from e

    @classmethod
    def from_json(cls, fp: Path) -> "Result":
        """Read a result from a JSON file."""

        if not fp.exists():
            raise FileNotFoundError(f"{fp} does not exist.")
        if not fp.is_file():
            raise ValueError(f"{fp} is not a file.")

        try:
            as_dict = json.loads(fp.read_text())
        except Exception as e:
            raise ValueError(f"Could not read result from {fp}") from e

        as_dict["timestamp"] = datetime.datetime.fromisoformat(as_dict["timestamp"])

        return cls(**as_dict)


CFG_YAML = files("MEDS_DEV.configs") / "_package_result.yaml"


__all__ = ["Result", "CFG_YAML"]
