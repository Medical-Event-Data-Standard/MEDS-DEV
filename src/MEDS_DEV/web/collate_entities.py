"""Collate dataset, task, and model entries into JSON manifests for the MEDS-DEV website.

The website (https://medical-event-data-standard.github.io) fetches three JSON files at runtime from the
``_web`` orphan branch of this repo:

- ``entities/datasets.json``
- ``entities/tasks.json``
- ``entities/models.json``

Each is a flat record keyed by entity name (relative path from ``src/MEDS_DEV/<datasets|tasks|models>/``),
with values shaped like::

    {
        "name": "<relative path>",
        "data": {
            "type": "dataset" | "task" | "model",
            "entity": <contents of dataset.yaml / task yaml / model.yaml>,
            "readme": <README.md text, optional>,
            "refs": <refs.bib text, optional>,
            "requirements": [<requirements.txt entries>, optional],
            "predicates": <predicates.yaml dict, datasets only>,
        },
        "children": [<names of nested entities, for category nodes>],
    }

This module produces those manifests deterministically from the source tree. See ``parse_tree.ts`` and
``types.ts`` in the website repo for the consumer-side schema.
"""

import argparse
import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from omegaconf import OmegaConf

EntityType = Literal["dataset", "task", "model"]

DATASETS_REL_PATH = Path("src/MEDS_DEV/datasets")
TASKS_REL_PATH = Path("src/MEDS_DEV/tasks")
MODELS_REL_PATH = Path("src/MEDS_DEV/models")

# Files whose presence in a leaf directory contributes to the ``data`` block.
# Keyed by file name; value is the JSON key used in the output.
LEAF_FILES: dict[str, str] = {
    "README.md": "readme",
    "refs.bib": "refs",
    "predicates.yaml": "predicates",
    "requirements.txt": "requirements",
}


@dataclass
class Node:
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)


def _read_file(path: Path) -> Any:
    """Read a single file from a leaf directory, dispatching by extension.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d) / "predicates.yaml"
        ...     _ = p.write_text("foo: bar\\n")
        ...     _read_file(p)
        {'foo': 'bar'}
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d) / "requirements.txt"
        ...     _ = p.write_text("numpy==1.21.0\\npandas==2.0.0\\n")
        ...     _read_file(p)
        ['numpy==1.21.0', 'pandas==2.0.0']
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d) / "README.md"
        ...     _ = p.write_text("# Title\\n")
        ...     _read_file(p)
        '# Title\\n'
    """
    if path.suffix == ".yaml":
        # ``???`` placeholders (Hydra missing values) are valid in MEDS-DEV task configs and must
        # survive serialization. ``to_container`` with ``throw_on_missing=False`` preserves them
        # as the literal string ``"???"``.
        return OmegaConf.to_container(OmegaConf.load(path), resolve=False, throw_on_missing=False)
    if path.suffix == ".txt":
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return path.read_text()


def _read_leaf_dir(leaf_dir: Path, entity_type: EntityType) -> dict[str, Any]:
    """Read the data block for a directory-based leaf (dataset or model).

    The ``<entity_type>.yaml`` file goes under ``entity``; sibling files matching
    ``LEAF_FILES`` go under their mapped keys.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     leaf = Path(d) / "MIMIC-IV"
        ...     leaf.mkdir()
        ...     _ = (leaf / "dataset.yaml").write_text("metadata:\\n  description: foo\\n")
        ...     _ = (leaf / "README.md").write_text("# MIMIC")
        ...     _ = (leaf / "requirements.txt").write_text("meds==0.3.3\\n")
        ...     data = _read_leaf_dir(leaf, "dataset")
        ...     sorted(data.keys())
        ['entity', 'readme', 'requirements', 'type']
        >>> data["type"]
        'dataset'
        >>> data["entity"]
        {'metadata': {'description': 'foo'}}
        >>> data["readme"]
        '# MIMIC'
        >>> data["requirements"]
        ['meds==0.3.3']
    """
    data: dict[str, Any] = {"type": entity_type}

    spec_path = leaf_dir / f"{entity_type}.yaml"
    if spec_path.is_file():
        data["entity"] = _read_file(spec_path)

    for fname, key in LEAF_FILES.items():
        sibling = leaf_dir / fname
        if sibling.is_file():
            data[key] = _read_file(sibling)

    return data


def _read_category_dir(category_dir: Path, entity_type: EntityType) -> dict[str, Any]:
    """Read the data block for a category directory.

    Categories carry a ``type`` and (optionally) a ``readme``. They never have an ``entity`` block
    of their own — that's reserved for leaves.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     cat = Path(d) / "abnormal_lab"
        ...     cat.mkdir()
        ...     _ = (cat / "README.md").write_text("Lab tasks")
        ...     _read_category_dir(cat, "task")
        {'type': 'task', 'readme': 'Lab tasks'}
        >>> with tempfile.TemporaryDirectory() as d:
        ...     cat = Path(d) / "empty"
        ...     cat.mkdir()
        ...     _read_category_dir(cat, "task")
        {'type': 'task'}
    """
    data: dict[str, Any] = {"type": entity_type}
    readme = category_dir / "README.md"
    if readme.is_file():
        data["readme"] = readme.read_text()
    return data


def _walk_ancestors(leaf: Path, root: Path) -> Iterator[Path]:
    """Yield each ancestor directory of ``leaf`` up to (not including) ``root``.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     root = Path(d)
        ...     leaf = root / "a" / "b" / "c"
        ...     [str(p.relative_to(root)) for p in _walk_ancestors(leaf, root)]
        ['a/b', 'a']
    """
    parent = leaf.parent
    while parent != root:
        yield parent
        if parent == parent.parent:  # pragma: no cover  # filesystem root reached
            return
        parent = parent.parent


def _add_category_chain(
    nodes: dict[str, Node],
    leaf_path: Path,
    leaf_name: str,
    root: Path,
    entity_type: EntityType,
) -> None:
    """Walk up from a leaf, registering category nodes (those with a README) and linking them as parents.

    Categories without a README are skipped silently — the chain "jumps over" them. This matches the prototype
    behavior and avoids polluting the output with empty intermediate nodes.
    """
    child_name = leaf_name
    for ancestor in _walk_ancestors(leaf_path, root):
        cat_data = _read_category_dir(ancestor, entity_type)
        if "readme" not in cat_data:
            continue
        cat_name = ancestor.relative_to(root).as_posix()
        if cat_name not in nodes:
            nodes[cat_name] = Node(name=cat_name, data=cat_data)
        if child_name not in nodes[cat_name].children:
            nodes[cat_name].children.append(child_name)
        child_name = cat_name


def _collate_dir_leaves(root: Path, entity_type: Literal["dataset", "model"]) -> dict[str, Node]:
    """Collate a tree where each leaf is a directory containing ``<entity_type>.yaml`` (datasets, models).

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     root = Path(d)
        ...     # MIMIC-IV (leaf only — no parent category README)
        ...     mimic = root / "MIMIC-IV"
        ...     mimic.mkdir()
        ...     _ = (mimic / "dataset.yaml").write_text("metadata:\\n  description: foo\\n")
        ...     _ = (mimic / "README.md").write_text("MIMIC text")
        ...     # nested MIMIC/III with parent category README
        ...     leaf = root / "MIMIC" / "III"
        ...     leaf.mkdir(parents=True)
        ...     _ = (leaf / "dataset.yaml").write_text("metadata: {description: bar}")
        ...     _ = (root / "MIMIC" / "README.md").write_text("MIMIC family")
        ...     nodes = _collate_dir_leaves(root, "dataset")
        ...     sorted(nodes.keys())
        ['MIMIC', 'MIMIC-IV', 'MIMIC/III']
        >>> nodes["MIMIC/III"].data["entity"]
        {'metadata': {'description': 'bar'}}
        >>> nodes["MIMIC"].children
        ['MIMIC/III']
        >>> nodes["MIMIC"].data["readme"]
        'MIMIC family'
    """
    nodes: dict[str, Node] = {}
    spec_name = f"{entity_type}.yaml"

    leaves = sorted(root.rglob(spec_name))
    for spec_path in leaves:
        leaf_dir = spec_path.parent
        name = leaf_dir.relative_to(root).as_posix()
        nodes[name] = Node(
            name=name,
            data=_read_leaf_dir(leaf_dir, entity_type),
        )
        _add_category_chain(nodes, leaf_dir, name, root, entity_type)

    return nodes


def _collate_task_files(root: Path) -> dict[str, Node]:
    """Collate the task tree where each leaf is a ``*.yaml`` file (not a directory).

    The task name is the relative path with the ``.yaml`` suffix stripped; the file's contents become the
    leaf's ``entity`` block. Category nodes come from ancestor directories that have a ``README.md``.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     root = Path(d)
        ...     # mortality/in_icu/first_24h.yaml
        ...     leaf = root / "mortality" / "in_icu"
        ...     leaf.mkdir(parents=True)
        ...     _ = (leaf / "first_24h.yaml").write_text("predicates: {a: b}")
        ...     # category READMEs
        ...     _ = (root / "mortality" / "README.md").write_text("Mortality tasks")
        ...     _ = (root / "mortality" / "in_icu" / "README.md").write_text("ICU mortality")
        ...     nodes = _collate_task_files(root)
        ...     sorted(nodes.keys())
        ['mortality', 'mortality/in_icu', 'mortality/in_icu/first_24h']
        >>> nodes["mortality/in_icu/first_24h"].data["entity"]
        {'predicates': {'a': 'b'}}
        >>> nodes["mortality/in_icu"].children
        ['mortality/in_icu/first_24h']
        >>> nodes["mortality"].children
        ['mortality/in_icu']
    """
    nodes: dict[str, Node] = {}

    leaves = sorted(root.rglob("*.yaml"))
    for yaml_path in leaves:
        name = yaml_path.relative_to(root).with_suffix("").as_posix()
        nodes[name] = Node(
            name=name,
            data={"type": "task", "entity": _read_file(yaml_path)},
        )
        _add_category_chain(nodes, yaml_path, name, root, "task")

    return nodes


def collate_datasets(repo_dir: Path) -> dict[str, dict[str, Any]]:
    """Collate dataset entries rooted at ``repo_dir / src / MEDS_DEV / datasets``."""
    nodes = _collate_dir_leaves(repo_dir / DATASETS_REL_PATH, "dataset")
    return {k: asdict(v) for k, v in nodes.items()}


def collate_tasks(repo_dir: Path) -> dict[str, dict[str, Any]]:
    """Collate task entries rooted at ``repo_dir / src / MEDS_DEV / tasks``."""
    nodes = _collate_task_files(repo_dir / TASKS_REL_PATH)
    return {k: asdict(v) for k, v in nodes.items()}


def collate_models(repo_dir: Path) -> dict[str, dict[str, Any]]:
    """Collate model entries rooted at ``repo_dir / src / MEDS_DEV / models``."""
    nodes = _collate_dir_leaves(repo_dir / MODELS_REL_PATH, "model")
    return {k: asdict(v) for k, v in nodes.items()}


def collate_entities(repo_dir: Path, output_dir: Path, do_overwrite: bool = False) -> None:
    """Write ``datasets.json``, ``tasks.json``, ``models.json`` to ``output_dir``.

    Args:
        repo_dir: Path to the MEDS-DEV repository (the directory containing ``src/MEDS_DEV/``).
        output_dir: Directory where the manifests will be written.
        do_overwrite: If ``False`` (default) and any output file already exists, raise.
            If ``True``, overwrite.

    Raises:
        FileNotFoundError: If ``repo_dir`` does not exist.
        NotADirectoryError: If ``repo_dir`` is not a directory.
        IsADirectoryError: If an output target exists as a directory.
        FileExistsError: If an output target exists and ``do_overwrite`` is ``False``.

    Examples:
        >>> import json, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     repo = Path(d) / "repo"
        ...     # Minimal source tree
        ...     leaf = repo / "src" / "MEDS_DEV" / "datasets" / "MIMIC-IV"
        ...     leaf.mkdir(parents=True)
        ...     _ = (leaf / "dataset.yaml").write_text("metadata:\\n  description: foo")
        ...     task_dir = repo / "src" / "MEDS_DEV" / "tasks" / "mortality" / "in_icu"
        ...     task_dir.mkdir(parents=True)
        ...     _ = (task_dir / "first_24h.yaml").write_text("predicates: {x: y}")
        ...     model_dir = repo / "src" / "MEDS_DEV" / "models" / "random_predictor"
        ...     model_dir.mkdir(parents=True)
        ...     _ = (model_dir / "model.yaml").write_text("metadata:\\n  description: rp")
        ...     out = Path(d) / "out"
        ...     collate_entities(repo, out, do_overwrite=True)
        ...     sorted(p.name for p in out.iterdir())
        ['datasets.json', 'models.json', 'tasks.json']
        >>> with tempfile.TemporaryDirectory() as d:
        ...     repo = Path(d) / "repo"
        ...     repo.mkdir()
        ...     out = Path(d) / "out"
        ...     out.mkdir()
        ...     _ = (out / "datasets.json").write_text("stale")
        ...     collate_entities(repo, out, do_overwrite=False)
        Traceback (most recent call last):
            ...
        FileExistsError: Output path ... already exists. Pass do_overwrite=True to replace.
        >>> collate_entities(Path("/nonexistent_path_xyz"), Path("/tmp"))
        Traceback (most recent call last):
            ...
        FileNotFoundError: Repository directory /nonexistent_path_xyz does not exist.
    """
    if not repo_dir.exists():
        raise FileNotFoundError(f"Repository directory {repo_dir!s} does not exist.")
    if not repo_dir.is_dir():
        raise NotADirectoryError(f"Repository path {repo_dir!s} is not a directory.")

    output_dir.mkdir(parents=True, exist_ok=True)

    targets: dict[str, dict[str, Any]] = {
        "datasets.json": collate_datasets(repo_dir),
        "tasks.json": collate_tasks(repo_dir),
        "models.json": collate_models(repo_dir),
    }

    for name in targets:
        fp = output_dir / name
        if fp.exists():
            if fp.is_dir():
                raise IsADirectoryError(f"Output path {fp!s} is a directory; refusing to write.")
            if not do_overwrite:
                raise FileExistsError(
                    f"Output path {fp!s} already exists. Pass do_overwrite=True to replace."
                )

    for name, payload in targets.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Collate MEDS-DEV entity manifests for the website.")
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
        help="Directory to write datasets.json, tasks.json, models.json into.",
    )
    parser.add_argument(
        "--do_overwrite",
        action="store_true",
        help="Overwrite existing manifest files instead of raising.",
    )
    args = parser.parse_args()
    collate_entities(args.repo_dir, args.output_dir, args.do_overwrite)


if __name__ == "__main__":  # pragma: no cover
    main()
