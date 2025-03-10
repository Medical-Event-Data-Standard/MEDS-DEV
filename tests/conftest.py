import contextlib
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import pytest

from MEDS_DEV import DATASETS, MODELS, TASKS
from tests.utils import NAME_AND_DIR, run_command

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--persistent_cache_dir",
        default=None,
        help=(
            "Use this local (preserved) directory for persistent caching. Directory must exist. Use the "
            "options --cache_dataset, --cache_task, and --cache_model to enable or disable caching for "
            "specific datasets, tasks, and models."
        ),
    )

    def add_cache_opt(opt: str):
        cache_str_template = (
            "Cache the {opt} with the given name. Use 'all' to cache all {opt}s. Add specific {opt}s "
            "by repeating the option, e.g., --cache_{opt}={opt}1 --cache_{opt}={opt}2."
        )
        parser.addoption(f"--cache_{opt}", action="append", type=str, help=cache_str_template.format(opt=opt))

    add_cache_opt("dataset")
    add_cache_opt("task")
    add_cache_opt("model")

    def add_test_opt(opt: str):
        test_str_template = (
            "Test the {opt} with the given name. Use 'all' to select all {opt}s. Add specific {opt}s "
            "by repeating the option, e.g., --test_{opt}={opt}1 --test_{opt}={opt}2. Default is to run all. "
            "If any are added, then only those will be run, but if none are added, then all will be run."
        )
        parser.addoption(f"--test_{opt}", action="append", type=str, help=test_str_template.format(opt=opt))

    add_test_opt("dataset")
    add_test_opt("task")
    add_test_opt("model")

    def add_reuse_opt(opt: str):
        reuse_str_template = (
            "If cached and tested, ensure that the following {opt} can be re-used across tests. Use 'all' to "
            "reuse all {opt}s. Add specific {opt}s by repeating the arg, e.g., --reuse_cached_{opt}={opt}1 "
            "--reuse_cached_{opt}={opt}2. Arguments for {opt}s that are not tested & cached will be ignored."
        )
        parser.addoption(
            f"--reuse_cached_{opt}", action="append", type=str, help=reuse_str_template.format(opt=opt)
        )

    add_reuse_opt("dataset")
    add_reuse_opt("task")
    add_reuse_opt("model")

    parser.addoption(
        "--do_clear_venvs",
        action="store_true",
        dest="clear_venvs",
        default=True,
        help="Clear the venvs for datasets and models after testing.",
    )

    parser.addoption(
        "--no_do_clear_venvs",
        action="store_false",
        dest="clear_venvs",
        help="Do not clear the venvs for datasets and models after testing.",
    )


def get_and_validate_cache_settings(request) -> tuple[Path, tuple[set[str], set[str], set[str]]]:
    """A helper to get the cache settings from the pytest parser options and return the appropriate options.

    Args:
        request: The pytest request object.

    Returns:
        A tuple with the persistent cache directory and a tuple with the sets for datasets, tasks, and models.
        If the persistent cache directory is None, the sets will be empty. If the persistent cache directory
        is not None and exists, the sets will be filled with the respective names. If any of the sets contain
        'all', they will be set to all valid options.

    Examples:
        >>> class MockRequest:
        ...     def __init__(self, persistent_cache_dir, cache_datasets, cache_tasks, cache_models):
        ...         self.opts = {
        ...             '--persistent_cache_dir': persistent_cache_dir,
        ...             '--cache_dataset': cache_datasets,
        ...             '--cache_task': cache_tasks,
        ...             '--cache_model': cache_models,
        ...         }
        ...         self.config = self
        ...     def getoption(self, opt):
        ...         return self.opts[opt]
        >>> get_and_validate_cache_settings(MockRequest(None, None, None, None))
        (None, (set(), set(), set()))
        >>> with TemporaryDirectory() as temp_dir:
        ...     cache_dir = Path(temp_dir) / "cache"
        ...     cache_dir.mkdir()
        ...     out = get_and_validate_cache_settings(MockRequest(cache_dir, None, None, None))
        ...     print(out[0].relative_to(Path(temp_dir)), out[1], len(out))
        cache (set(), set(), set()) 2
        >>> with TemporaryDirectory() as temp_dir:
        ...     cache_dir = Path(temp_dir) / "cache"
        ...     cache_dir.mkdir()
        ...     out = get_and_validate_cache_settings(MockRequest(cache_dir, ["d1", "d2"], ["t1"], []))
        ...     print(out[0].relative_to(Path(temp_dir)), tuple(sorted(x) for x in out[1]), len(out))
        cache (['d1', 'd2'], ['t1'], []) 2
        >>> with TemporaryDirectory() as temp_dir:
        ...     cache_dir = Path(temp_dir) / "cache_dir"
        ...     cache_dir.mkdir()
        ...     out = get_and_validate_cache_settings(MockRequest(cache_dir, ["d1", "d2", "all"], [], ["m1"]))
        ...     assert out[0] == cache_dir, f"Expected {cache_dir}, got {out[0]}"
        ...     assert len(out) == 2, f"Expected 2, got {len(out)}"
        ...     assert out[1] == (set(DATASETS), set(), {"m1"}), (
        ...         f"Want ({set(DATASETS)}, [], {{'m1'}}) got {out[1]}"
        ...     )
        >>> get_and_validate_cache_settings(MockRequest(None, ["d1", "d2", "all"], [], ["m1"]))
        Traceback (most recent call last):
            ...
        _pytest.config.exceptions.UsageError: Persistent cache directory must be set if any cache options are!
        >>> with TemporaryDirectory() as temp_dir:
        ...     cache_dir = Path(temp_dir) / "cache_dir"
        ...     get_and_validate_cache_settings(MockRequest(cache_dir, [], [], []))
        Traceback (most recent call last):
            ...
        _pytest.config.exceptions.UsageError: Persistent cache directory must be an existent directory!
    """
    persistent_cache_dir = request.config.getoption("--persistent_cache_dir")
    cache_datasets = request.config.getoption("--cache_dataset")
    cache_tasks = request.config.getoption("--cache_task")
    cache_models = request.config.getoption("--cache_model")
    if (cache_datasets or cache_tasks or cache_models) and not persistent_cache_dir:
        raise pytest.UsageError("Persistent cache directory must be set if any cache options are!")

    if not persistent_cache_dir:
        return None, (set(), set(), set())

    persistent_cache_dir = Path(persistent_cache_dir)
    if not persistent_cache_dir.is_dir():
        raise pytest.UsageError("Persistent cache directory must be an existent directory!")

    datasets_set = set(cache_datasets) if cache_datasets else set()
    if "all" in datasets_set:
        datasets_set = set(DATASETS)
    tasks_set = set(cache_tasks) if cache_tasks else set()
    if "all" in tasks_set:
        tasks_set = set(TASKS)
    models_set = set(cache_models) if cache_models else set()
    if "all" in models_set:
        models_set = set(MODELS)

    return persistent_cache_dir, (datasets_set, tasks_set, models_set)


def get_and_validate_reuse_settings(request) -> tuple[set[str], set[str], set[str]]:
    """A helper to check the pytest parser options for reuse and return the appropriate options.

    Args:
        request: The pytest request object.

    Returns:
        A tuple of the sets for datasets, tasks, and models that should be reused across tests. If any of the
        sets contain 'all', they will be set to all valid options.

    Examples:
        >>> class MockRequest:
        ...     def __init__(self, reuse_cached_datasets, reuse_cached_tasks, reuse_cached_models):
        ...         self.opts = {
        ...             '--reuse_cached_dataset': reuse_cached_datasets,
        ...             '--reuse_cached_task': reuse_cached_tasks,
        ...             '--reuse_cached_model': reuse_cached_models,
        ...         }
        ...         self.config = self
        ...     def getoption(self, opt):
        ...         return self.opts[opt]
        >>> get_and_validate_reuse_settings(MockRequest(None, None, None))
        (set(), set(), set())
        >>> out = get_and_validate_reuse_settings(MockRequest(["d1", "d2"], ["t1"], ["m1"]))
        >>> print(tuple(sorted(list(x)) for x in out))
        (['d1', 'd2'], ['t1'], ['m1'])
        >>> D, T, M = get_and_validate_reuse_settings(MockRequest(["d1", "d2", "all"], ["all"], ["all"]))
        >>> assert D == set(DATASETS), f"Expected {set(DATASETS)}, got {D}"
        >>> assert T == set(TASKS), f"Expected {set(TASKS)}, got {T}"
        >>> assert M == set(MODELS), f"Expected {set(MODELS)}, got {M}"
    """
    reuse_cached_datasets = request.config.getoption("--reuse_cached_dataset")
    reuse_cached_tasks = request.config.getoption("--reuse_cached_task")
    reuse_cached_models = request.config.getoption("--reuse_cached_model")

    datasets_set = set(reuse_cached_datasets) if reuse_cached_datasets else set()
    if "all" in datasets_set:
        datasets_set = set(DATASETS)
    tasks_set = set(reuse_cached_tasks) if reuse_cached_tasks else set()
    if "all" in tasks_set:
        tasks_set = set(TASKS)
    models_set = set(reuse_cached_models) if reuse_cached_models else set()
    if "all" in models_set:
        models_set = set(MODELS)

    return datasets_set, tasks_set, models_set


@contextlib.contextmanager
def cache_dir(persistent_dir: Path | None):
    """A simple helper to yield either the persistent dir or a temporary directory.

    Args:
        persistent_dir (Path | None): A Path object to a persistent directory that should be used or None.

    Yields: Either the persistent directory if it is not None or a temporary directory.

    Examples:
        >>> with cache_dir(Path("my_dir")) as root_dir:
        ...     print(str(root_dir))
        my_dir
        >>> with cache_dir(None) as root_dir:
        ...     print(str(root_dir))
        /tmp/...
    """
    if persistent_dir:
        yield Path(persistent_dir)
    else:
        with TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)


def get_opts(config, opt: str) -> list[str]:
    """A helper to get the options from the config object, pulling from all supported where appropriate."""
    arg = config.getoption(f"--test_{opt}")
    allowed = {"dataset": DATASETS, "task": TASKS, "model": MODELS}

    if arg:
        return allowed[opt] if "all" in arg else arg
    else:
        return allowed[opt]


def pytest_generate_tests(metafunc):
    if "demo_dataset" in metafunc.fixturenames:
        metafunc.parametrize("demo_dataset", get_opts(metafunc.config, "dataset"), indirect=True)
    if "task_labels" in metafunc.fixturenames:
        metafunc.parametrize("task_labels", get_opts(metafunc.config, "task"), indirect=True)
    if "unsupervised_model" in metafunc.fixturenames:
        metafunc.parametrize("unsupervised_model", get_opts(metafunc.config, "model"), indirect=True)


@pytest.fixture(scope="session")
def venv_cache(request) -> Path | None:
    with cache_dir(request.config.getoption("--persistent_cache_dir")) as cache:
        yield cache / "venvs"


@pytest.fixture(scope="session")
def demo_dataset(request, venv_cache: Path) -> NAME_AND_DIR:
    dataset_name = request.param
    persistent_cache_dir, (cache_datasets, _, _) = get_and_validate_cache_settings(request)
    reuse_datasets, _, _ = get_and_validate_reuse_settings(request)

    do_overwrite = not (dataset_name in reuse_datasets)

    with cache_dir(persistent_cache_dir if dataset_name in cache_datasets else None) as root_dir:
        root_dir = Path(root_dir)

        check_fp = root_dir / f".{dataset_name}.check"
        output_dir = root_dir / dataset_name

        data_exists = (output_dir / "data").is_dir()
        metadata_exists = (output_dir / "metadata").is_dir()

        already_tested = check_fp.exists() and data_exists and metadata_exists
        if do_overwrite or not already_tested:
            venv_dir = venv_cache / "datasets" / dataset_name

            run_command(
                "meds-dev-dataset",
                test_name=f"Build {dataset_name}",
                hydra_kwargs={
                    "dataset": dataset_name,
                    "output_dir": str(output_dir.resolve()),
                    "demo": True,
                    "venv_dir": str(venv_dir.resolve()),
                },
            )

            # Dataset venvs should never be used again, so we delete it here for simplicity.
            if request.config.getoption("clear_venvs") and venv_dir.is_dir():
                logger.info(f"Deleting venv for {dataset_name} at {venv_dir}")
                shutil.rmtree(venv_dir)

            check_fp.parent.mkdir(parents=True, exist_ok=True)
            check_fp.touch()

        yield dataset_name, output_dir


@pytest.fixture(scope="session")
def task_labels(request, demo_dataset: NAME_AND_DIR) -> NAME_AND_DIR:
    task_name = request.param
    dataset_name, dataset_dir = demo_dataset

    _, reuse_tasks, _ = get_and_validate_reuse_settings(request)

    do_overwrite = not (task_name in reuse_tasks)

    task_metadata = TASKS[task_name].get("metadata", None)
    if task_metadata is None or dataset_name not in task_metadata.supported_datasets:
        pytest.skip(f"Dataset {dataset_name} not supported for testing {task_name}.")

    persistent_cache_dir, (_, cache_tasks, _) = get_and_validate_cache_settings(request)
    with cache_dir(persistent_cache_dir if task_name in cache_tasks else None) as root_dir:
        root_dir = Path(root_dir)
        task_labels_dir = root_dir / dataset_name / "task_labels" / task_name

        check_fp = root_dir / f".{dataset_name}.{task_name}.check"
        labels_exist = task_labels_dir.is_dir() and any(task_labels_dir.rglob("*.parquet"))

        already_tested = check_fp.exists() and labels_exist

        if do_overwrite or not already_tested:
            run_command(
                "meds-dev-task",
                test_name=f"Extract {task_name}",
                hydra_kwargs={
                    "task": task_name,
                    "dataset": dataset_name,
                    "dataset_dir": str(dataset_dir.resolve()),
                    "output_dir": str(task_labels_dir.resolve()),
                },
            )
            check_fp.parent.mkdir(parents=True, exist_ok=True)
            check_fp.touch()

        yield task_name, task_labels_dir


def missing_labels_in_splits(labels_dir: Path, dataset_dir: Path) -> set[str]:
    """If any splits (defined in the dataset metadata) are missing any labels, return them.

    Args:
        labels_dir (Path): The directory with the labels.
        dataset_dir (Path): The directory with the dataset.

    Returns:
        A set of split names that are missing labels.

    Examples:
        >>> splits = pl.DataFrame({"subject_id": [1, 2, 3], "split": ["train", "tuning", "held_out"]})
        >>> labels = pl.DataFrame({"subject_id": [1, 3]}) # This is not a true label schema
        >>> with TemporaryDirectory() as temp_dir:
        ...     labels_dir = Path(temp_dir) / "labels"
        ...     labels_dir.mkdir()
        ...     labels.write_parquet(labels_dir / "0.parquet")
        ...     dataset_dir = Path(temp_dir) / "dataset"
        ...     metadata_dir = dataset_dir / "metadata"
        ...     metadata_dir.mkdir(parents=True)
        ...     splits.write_parquet(metadata_dir / "subject_splits.parquet")
        ...     missing_labels_in_splits(labels_dir, dataset_dir)
        {'tuning'}
        >>> labels = pl.DataFrame({"subject_id": [2, 3]}) # This is not a true label schema
        >>> with TemporaryDirectory() as temp_dir:
        ...     labels_dir = Path(temp_dir) / "labels"
        ...     labels_dir.mkdir()
        ...     labels.write_parquet(labels_dir / "0.parquet")
        ...     dataset_dir = Path(temp_dir) / "dataset"
        ...     metadata_dir = dataset_dir / "metadata"
        ...     metadata_dir.mkdir(parents=True)
        ...     splits.write_parquet(metadata_dir / "subject_splits.parquet")
        ...     missing_labels_in_splits(labels_dir, dataset_dir)
        {'train'}
        >>> labels = pl.DataFrame({"subject_id": [2, 2]}) # This is not a true label schema
        >>> with TemporaryDirectory() as temp_dir:
        ...     labels_dir = Path(temp_dir) / "labels"
        ...     labels_dir.mkdir()
        ...     labels.write_parquet(labels_dir / "0.parquet")
        ...     dataset_dir = Path(temp_dir) / "dataset"
        ...     metadata_dir = dataset_dir / "metadata"
        ...     metadata_dir.mkdir(parents=True)
        ...     splits.write_parquet(metadata_dir / "subject_splits.parquet")
        ...     sorted(missing_labels_in_splits(labels_dir, dataset_dir))
        ['held_out', 'train']
        >>> labels = pl.DataFrame({"subject_id": [1, 2, 3]}) # This is not a true label schema
        >>> with TemporaryDirectory() as temp_dir:
        ...     labels_dir = Path(temp_dir) / "labels"
        ...     labels_dir.mkdir()
        ...     labels.write_parquet(labels_dir / "0.parquet")
        ...     dataset_dir = Path(temp_dir) / "dataset"
        ...     metadata_dir = dataset_dir / "metadata"
        ...     metadata_dir.mkdir(parents=True)
        ...     splits.write_parquet(metadata_dir / "subject_splits.parquet")
        ...     missing_labels_in_splits(labels_dir, dataset_dir)
        set()
    """

    labels = pl.concat(
        [pl.read_parquet(f, use_pyarrow=True, columns=["subject_id"]) for f in labels_dir.rglob("*.parquet")],
        how="vertical_relaxed",
    )
    label_subjects = set(labels["subject_id"].unique())

    subject_splits = pl.read_parquet(dataset_dir / "metadata" / "subject_splits.parquet", use_pyarrow=True)
    all_splits = set(subject_splits["split"].unique())

    subj_splits_with_label = subject_splits.filter(pl.col("subject_id").is_in(label_subjects))
    splits_with_labels = set(subj_splits_with_label["split"].unique())

    return all_splits - splits_with_labels


@pytest.fixture(scope="session")
def unsupervised_model(request, demo_dataset: NAME_AND_DIR, venv_cache: Path) -> NAME_AND_DIR:
    model = request.param

    unsupervised_commands = MODELS[model]["commands"].get("unsupervised", None)
    if not unsupervised_commands:
        yield model, None
        return
    if not unsupervised_commands.get("train", None):
        yield model, None
        return

    dataset_name, dataset_dir = demo_dataset

    _, _, reuse_models = get_and_validate_reuse_settings(request)

    do_overwrite = not (model in reuse_models)

    persistent_cache_dir, (_, _, cache_models) = get_and_validate_cache_settings(request)

    with cache_dir(persistent_cache_dir if model in cache_models else None) as root_dir:
        check_fp = root_dir / f".{model}._unsupervised..{dataset_name}.check"
        model_dir = root_dir / model

        already_tested = check_fp.exists() and model_dir.is_dir()

        if do_overwrite or not already_tested:
            venv_dir = venv_cache / "models" / model

            run_command(
                "meds-dev-model",
                test_name=f"Model {model} should train in unsupervised mode on {dataset_name}",
                hydra_kwargs={
                    "model": model,
                    "dataset_type": "unsupervised",
                    "mode": "train",
                    "dataset_dir": str(dataset_dir.resolve()),
                    "dataset_name": dataset_name,
                    "output_dir": str(model_dir.resolve()),
                    "demo": True,
                    "venv_dir": str(venv_dir.resolve()),
                },
            )
            check_fp.parent.mkdir(parents=True, exist_ok=True)
            check_fp.touch()

        yield model, model_dir


@pytest.fixture(scope="session")
def supervised_model(
    request,
    unsupervised_model: NAME_AND_DIR,
    demo_dataset: NAME_AND_DIR,
    task_labels: NAME_AND_DIR,
    venv_cache: Path,
) -> NAME_AND_DIR:
    model, unsupervised_train_dir = unsupervised_model

    dataset_name, dataset_dir = demo_dataset
    task_name, task_labels_dir = task_labels

    missing_splits = missing_labels_in_splits(task_labels_dir, dataset_dir)
    if missing_splits:
        pytest.skip(
            f"Labels not found for {dataset_name} and {task_name} in split(s): {', '.join(missing_splits)}. "
            f"Skipping {model} test."
        )

    _, _, reuse_models = get_and_validate_reuse_settings(request)

    do_overwrite = not (model in reuse_models)

    persistent_cache_dir, (_, _, cache_models) = get_and_validate_cache_settings(request)

    shared_kwargs = {
        "model": model,
        "dataset_type": "supervised",
        "mode": "full",
        "dataset_dir": str(dataset_dir.resolve()),
        "labels_dir": str(task_labels_dir.resolve()),
        "dataset_name": dataset_name,
        "task_name": task_name,
        "demo": True,
    }
    if unsupervised_train_dir is not None:
        shared_kwargs["model_initialization_dir"] = str(unsupervised_train_dir.resolve())

    with cache_dir(persistent_cache_dir if model in cache_models else None) as root_dir:
        check_fp = root_dir / f".{model}.{dataset_name}.{task_name}.check"
        model_dir = root_dir / model

        already_tested = check_fp.exists() and model_dir.is_dir()

        if do_overwrite or not already_tested:
            venv_dir = venv_cache / "models" / model

            run_command(
                "meds-dev-model",
                test_name=f"Model {model} should run on {dataset_name} and {task_name}",
                hydra_kwargs={
                    **shared_kwargs,
                    "output_dir": str(model_dir.resolve()),
                    "venv_dir": str(venv_dir.resolve()),
                },
            )
            check_fp.parent.mkdir(parents=True, exist_ok=True)
            check_fp.touch()

        final_out_dir = model_dir / dataset_name / task_name / "predict"
        yield model, final_out_dir


@pytest.fixture(scope="session")
def evaluated_model(supervised_model: NAME_AND_DIR) -> Path:
    model, final_out_dir = supervised_model

    with TemporaryDirectory() as root_dir:
        run_command(
            "meds-dev-evaluation",
            test_name=f"Evaluate {model}",
            hydra_kwargs={
                "output_dir": str(root_dir),
                "predictions_dir": str(final_out_dir),
            },
        )

        yield Path(root_dir)
