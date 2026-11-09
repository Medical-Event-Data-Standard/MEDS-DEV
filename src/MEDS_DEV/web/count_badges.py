"""Write shields.io badges showing how many datasets, tasks, and models MEDS-DEV registers.

The badges in the top-level README are rendered by shields.io from three JSON files on the ``_web`` orphan
branch of this repo:

- ``badges/datasets.json``
- ``badges/tasks.json``
- ``badges/models.json``

``regenerate_entities.yaml`` rewrites them together with the entity manifests on every push to ``main`` that
touches a dataset, task, or model, so the counts follow ``main`` without anyone editing the README. Each file
uses the shields.io [endpoint schema](https://shields.io/badges/endpoint-badge)::

    {"schemaVersion": 1, "label": "datasets", "message": "10", "color": "blue"}

The counts use the same globs as the ``DATASETS``, ``TASKS`` and ``MODELS`` registries: a dataset is a
directory holding a ``dataset.yaml``, a model is a directory holding a ``model.yaml`` (so each size of a
model, such as ``meds_tab/tiny``, counts once), and a task is a ``.yaml`` file under ``tasks/``. Category
directories that only hold a ``README.md`` are not counted.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from .collate_entities import DATASETS_REL_PATH, MODELS_REL_PATH, TASKS_REL_PATH

BADGE_COLOR = "blue"


def count_entities(repo_dir: Path) -> dict[str, int]:
    """Count the datasets, tasks, and models in the source tree of a MEDS-DEV repository.

    Args:
        repo_dir: Path to the MEDS-DEV repository (the directory containing ``src/MEDS_DEV/``).

    Returns:
        A dictionary with the keys ``datasets``, ``tasks`` and ``models``. A missing entity directory counts
        as zero.

    Examples:
        >>> tree = '''
        ... src/MEDS_DEV/:
        ...   datasets/:
        ...     MIMIC-IV/:
        ...       dataset.yaml: {metadata: {description: foo}}
        ...     eICU/:
        ...       dataset.yaml: {metadata: {description: bar}}
        ...       predicates.yaml: {predicates: {}}
        ...   tasks/:
        ...     mortality/:
        ...       README.md: Mortality tasks
        ...       in_icu/:
        ...         first_24h.yaml: {predicates: {a: b}}
        ...     abnormal_lab/cbc/anemia/first_24h.yaml: {predicates: {c: d}}
        ...   models/:
        ...     meds_tab/:
        ...       README.md: MEDS-Tab family
        ...       tiny/:
        ...         model.yaml: {metadata: {description: tiny}}
        ...     random_predictor/:
        ...       model.yaml: {metadata: {description: rp}}
        ... '''
        >>> with yaml_disk(tree) as repo:
        ...     count_entities(repo)
        {'datasets': 2, 'tasks': 2, 'models': 2}
        >>> with yaml_disk({"README.md": "empty repo"}) as repo:
        ...     count_entities(repo)
        {'datasets': 0, 'tasks': 0, 'models': 0}
    """
    return {
        "datasets": len(list((repo_dir / DATASETS_REL_PATH).rglob("*/dataset.yaml"))),
        "tasks": len(list((repo_dir / TASKS_REL_PATH).glob("**/*.yaml"))),
        "models": len(list((repo_dir / MODELS_REL_PATH).rglob("*/model.yaml"))),
    }


def count_badge(label: str, count: int) -> dict[str, Any]:
    """Build a shields.io endpoint badge payload for one count.

    Examples:
        >>> count_badge("datasets", 10)
        {'schemaVersion': 1, 'label': 'datasets', 'message': '10', 'color': 'blue'}
    """
    return {"schemaVersion": 1, "label": label, "message": str(count), "color": BADGE_COLOR}


def write_count_badges(repo_dir: Path, output_dir: Path, do_overwrite: bool = False) -> dict[str, int]:
    """Write ``datasets.json``, ``tasks.json`` and ``models.json`` badge files to ``output_dir``.

    Args:
        repo_dir: Path to the MEDS-DEV repository (the directory containing ``src/MEDS_DEV/``).
        output_dir: Directory where the badge files will be written. It is created if needed.
        do_overwrite: If ``False`` (default) and any badge file already exists, raise. If ``True``, overwrite.

    Returns:
        The counts written, as returned by `count_entities`.

    Raises:
        FileNotFoundError: If ``repo_dir`` does not exist.
        NotADirectoryError: If ``repo_dir`` is not a directory.
        IsADirectoryError: If an output target exists as a directory.
        FileExistsError: If an output target exists and ``do_overwrite`` is ``False``.

    Examples:
        >>> tree = '''
        ... repo/src/MEDS_DEV/:
        ...   datasets/MIMIC-IV/dataset.yaml: {metadata: {description: foo}}
        ...   tasks/mortality/in_icu/first_24h.yaml: {predicates: {x: y}}
        ...   models/random_predictor/model.yaml: {metadata: {description: rp}}
        ... '''
        >>> with yaml_disk(tree) as d:
        ...     write_count_badges(d / "repo", d / "badges")
        ...     print_directory(d / "badges")
        ...     print((d / "badges" / "datasets.json").read_text())
        {'datasets': 1, 'tasks': 1, 'models': 1}
        ├── datasets.json
        ├── models.json
        └── tasks.json
        {"color": "blue", "label": "datasets", "message": "1", "schemaVersion": 1}

    Existing badge files without ``do_overwrite=True`` are an error, and so are a non-directory repo or a
    directory at one of the output paths:

        >>> with yaml_disk({"repo/.gitkeep": "", "badges/tasks.json": "stale"}) as d:
        ...     write_count_badges(d / "repo", d / "badges")
        Traceback (most recent call last):
            ...
        FileExistsError: Output path ... already exists. Pass do_overwrite=True to replace.
        >>> with yaml_disk({"repo/.gitkeep": "", "badges/tasks.json": "stale"}) as d:
        ...     write_count_badges(d / "repo", d / "badges", do_overwrite=True)
        ...     print((d / "badges" / "tasks.json").read_text())
        {'datasets': 0, 'tasks': 0, 'models': 0}
        {"color": "blue", "label": "tasks", "message": "0", "schemaVersion": 1}
        >>> write_count_badges(Path("/nonexistent_path_xyz"), Path("/tmp"))
        Traceback (most recent call last):
            ...
        FileNotFoundError: Repository directory /nonexistent_path_xyz does not exist.
        >>> with yaml_disk({"a.txt": "scalar"}) as d:
        ...     write_count_badges(d / "a.txt", d / "badges")
        Traceback (most recent call last):
            ...
        NotADirectoryError: Repository path ... is not a directory.
        >>> with yaml_disk({"repo/.gitkeep": "", "badges/models.json/.gitkeep": ""}) as d:
        ...     write_count_badges(d / "repo", d / "badges", do_overwrite=True)
        Traceback (most recent call last):
            ...
        IsADirectoryError: Output path ... is a directory; refusing to write.
    """
    if not repo_dir.exists():
        raise FileNotFoundError(f"Repository directory {repo_dir!s} does not exist.")
    if not repo_dir.is_dir():
        raise NotADirectoryError(f"Repository path {repo_dir!s} is not a directory.")

    counts = count_entities(repo_dir)
    output_paths = {label: output_dir / f"{label}.json" for label in counts}

    for fp in output_paths.values():
        if not fp.exists():
            continue
        if fp.is_dir():
            raise IsADirectoryError(f"Output path {fp!s} is a directory; refusing to write.")
        if not do_overwrite:
            raise FileExistsError(f"Output path {fp!s} already exists. Pass do_overwrite=True to replace.")

    output_dir.mkdir(parents=True, exist_ok=True)
    for label, fp in output_paths.items():
        fp.write_text(json.dumps(count_badge(label, counts[label]), sort_keys=True))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Write shields.io badges counting MEDS-DEV entities.")
    parser.add_argument(
        "--repo_dir",
        type=Path,
        default=Path.cwd(),
        help="Path to the MEDS-DEV repository (default: current directory).",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        required=True,
        help="Directory to write datasets.json, tasks.json, models.json badge files into.",
    )
    parser.add_argument(
        "--do_overwrite",
        action="store_true",
        help="Overwrite existing badge files instead of raising.",
    )
    args = parser.parse_args()
    counts = write_count_badges(args.repo_dir, args.output_dir, args.do_overwrite)
    print(json.dumps(counts))
