import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


def read_yaml(fp: Path) -> dict[str, Any]:
    return yaml.safe_load(fp.read_text())


def read_requirements(fp: Path) -> list[str]:
    return [line.strip() for line in fp.read_text().splitlines()]


FILETYPES = {
    ".yaml": ({"dataset.yaml", "model.yaml", "task.yaml", "predicates.yaml"}, read_yaml),
    ".md": ({"README.md"}, Path.read_text),
    ".bib": ({"refs.bib"}, Path.read_text),
    ".txt": ({"requirements.txt"}, read_requirements),
}

SRC_REL_PATH = Path("src/MEDS_DEV/")
DATASETS_REL_PATH = SRC_REL_PATH / "datasets"
TASKS_REL_PATH = SRC_REL_PATH / "tasks"
MODELS_REL_PATH = SRC_REL_PATH / "models"


@dataclass
class Node:
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)

    @staticmethod
    def data_from_leaf(leaf: Path) -> dict[str, Any]:
        """Parses a directory to extract its contents into a dictionary.

        Args:
            leaf: The directory to parse.

        Returns:
            A dictionary representation of the directory's valid file-type contents, which includes README.md,
            refs.bib, predicates.yaml, dataset.yaml, model.yaml, task.yaml, and requirements.txt files.

        Raises:
            FileNotFoundError: If the directory does not exist.
            NotADirectoryError: If the path is not a directory.

        Examples:
            >>> test_disk = '''
            ...   leaf1:
            ...     dataset.yaml: {"foo": "bar"}
            ...     README.md: "# README"
            ...     refs.bib: "@article{foo, bar}"
            ...   leaf2:
            ...     model.yaml: {"baz": "qux"}
            ...     requirements.txt: |-2
            ...       numpy==1.21.0
            ...       pandas==1.3.0
            ...     subdir:
            ...       README.md: "This is a README for the subdir. It won't show up."
            ...   leaf3:
            ...     - wrong_name.yaml
            ...     - wrong_suffix.csv
            ... '''
            >>> with yaml_disk(test_disk) as root_dir:
            ...     print(Node.data_from_leaf(root_dir / "leaf1"))
            {'README.md': '# README', 'dataset.yaml': {'foo': 'bar'}, 'refs.bib': '@article{foo, bar}'}
            >>> with yaml_disk(test_disk) as root_dir:
            ...     print(Node.data_from_leaf(root_dir / "leaf2"))
            {'model.yaml': {'baz': 'qux'}, 'requirements.txt': ['numpy==1.21.0', 'pandas==1.3.0']}
            >>> with yaml_disk(test_disk) as root_dir:
            ...     print(Node.data_from_leaf(root_dir / "leaf3"))
            {}

        Errors will be raised if the directory does not exist or is not a directory.

            >>> with yaml_disk(test_disk) as root_dir:
            ...     print(Node.data_from_leaf(root_dir / "leaf4"))
            Traceback (most recent call last):
                ...
            FileNotFoundError: Leaf directory /tmp/tmp.../leaf4 does not exist.
            >>> with yaml_disk(test_disk) as root_dir:
            ...     print(Node.data_from_leaf(root_dir / "leaf1" / "dataset.yaml"))
            Traceback (most recent call last):
                ...
            NotADirectoryError: Leaf /tmp/tmp.../leaf1/dataset.yaml is not a directory.
        """
        if not leaf.exists():
            raise FileNotFoundError(f"Leaf directory {leaf!s} does not exist.")
        if not leaf.is_dir():
            raise NotADirectoryError(f"Leaf {leaf!s} is not a directory.")

        data = {}
        for file in sorted(leaf.iterdir()):
            if not file.is_file():
                continue

            sfx = "".join(file.suffixes)
            if sfx not in FILETYPES:
                continue

            allowed_names, reader = FILETYPES[sfx]
            if file.name in allowed_names:
                data[file.name] = reader(file)
        return data


def parse_nested_tree(root: Path, base_glob: str) -> dict[str, Node]:
    """Parses a directory containing nested paths to a base glob into a dictionary structure.

    Args:
        root: The root directory to start parsing from.
        base_glob: The base glob pattern to match the "indicator" file that denotes a leaf node.

    Returns:
        A dictionary representation of the tree structure.

    Examples:
        >>> test_disk = '''
        ...   datasets:
        ...     MIMIC:
        ...       README.md: "This is a README for the category."
        ...       III:
        ...         dataset.yaml: {"foo": "bar"}
        ...         README.md: "This is a README."
        ...         refs.bib: "@article{foo, bar}"
        ...         predicates.yaml: {"predicate": "value"}
        ...         requirements.txt: |-2
        ...           numpy==1.21.0
        ...           pandas==1.3.0
        ...       IV:
        ...         dataset.yaml: {"foo": "baz"}
        ...         README.md: "This is another README."
        ...         refs.bib: "@article{baz, qux}"
        ...         predicates.yaml: {"predicate": "alt_value"}
        ...         requirements.txt: |-2
        ...           numpy==1.21.0
        ...           pandas==1.3.0
        ...     eICU:
        ...       dataset.yaml: {"foo": "quux"}
        ...       predicates.yaml: {"predicate": "quuz"}
        ...   tasks:
        ...     mortality:
        ...       README.md: "This is a README for the task."
        ...       in_icu:
        ...         first_24h:
        ...           README.md: "This is a README for the mortality/in_icu/first_24h task."
        ...           task.yaml: {"task": "value"}
        ...     readmission:
        ...       30d:
        ...         README.md: "This is a README for the readmission/30d task."
        ...         task.yaml: {"task": "value"}
        ...   models:
        ...     cehrbert:
        ...       README.md: "This is a README for the model."
        ...       model.yaml: {"model": "value"}
        ...       refs.bib: "@article{model, paper}"
        ...       requirements.txt: "numpy==1.21.0"
        ... '''
        >>> with yaml_disk(test_disk) as root_dir:
        ...     print(parse_nested_tree(root_dir, "dataset.yaml"))
        {'datasets/MIMIC/III': Node(name='datasets/MIMIC/III',
                                    data={'README.md': 'This is a README.',
                                          'dataset.yaml': {'foo': 'bar'},
                                          'predicates.yaml': {'predicate': 'value'},
                                          'refs.bib': '@article{foo, bar}',
                                          'requirements.txt': ['numpy==1.21.0', 'pandas==1.3.0']},
                                    children=[]),
         'datasets/MIMIC': Node(name='datasets/MIMIC',
                                data={'README.md': 'This is a README for the category.'},
                                children=['datasets/MIMIC/III', 'datasets/MIMIC/IV']),
         'datasets/MIMIC/IV': Node(name='datasets/MIMIC/IV',
                                   data={'README.md': 'This is another README.',
                                         'dataset.yaml': {'foo': 'baz'},
                                         'predicates.yaml': {'predicate': 'alt_value'},
                                         'refs.bib': '@article{baz, qux}',
                                         'requirements.txt': ['numpy==1.21.0', 'pandas==1.3.0']},
                                   children=[]),
         'datasets/eICU': Node(name='datasets/eICU',
                               data={'dataset.yaml': {'foo': 'quux'},
                               'predicates.yaml': {'predicate': 'quuz'}},
                               children=[])}
        >>> with yaml_disk(test_disk) as root_dir:
        ...     print(parse_nested_tree(root_dir, "task.yaml"))
        {'tasks/mortality/in_icu/first_24h': Node(name='tasks/mortality/in_icu/first_24h',
                                                  data={'README.md': 'This is a README for the
                                                                      mortality/in_icu/first_24h task.',
                                                        'task.yaml': {'task': 'value'}},
                                                  children=[]),
         'tasks/mortality': Node(name='tasks/mortality',
                                 data={'README.md': 'This is a README for the task.'},
                                 children=['tasks/mortality/in_icu/first_24h']),
         'tasks/readmission/30d': Node(name='tasks/readmission/30d',
                                       data={'README.md': 'This is a README for the readmission/30d task.',
                                             'task.yaml': {'task': 'value'}},
                                       children=[])}
        >>> with yaml_disk(test_disk) as root_dir:
        ...     print(parse_nested_tree(root_dir, "model.yaml"))
        {'models/cehrbert': Node(name='models/cehrbert',
                                 data={'README.md': 'This is a README for the model.',
                                       'model.yaml': {'model': 'value'},
                                       'refs.bib': '@article{model, paper}',
                                       'requirements.txt': ['numpy==1.21.0']},
                                 children=[])}
        >>> with yaml_disk(test_disk) as root_dir:
        ...     print(parse_nested_tree(root_dir, "non_existent.yaml"))
        {}
    """
    fps = list(root.rglob(base_glob))

    nodes = {}
    for fp in fps:
        rel_path = fp.relative_to(root)
        name = str(rel_path.parent.as_posix())
        data = Node.data_from_leaf(fp.parent)
        nodes[name] = Node(name=name, data=data)

        child_name = name
        parent_path = fp.parent
        while parent_path != root:
            parent_path = parent_path.parent
            parent_data = Node.data_from_leaf(parent_path)

            if not parent_data:
                continue

            parent_name = str(parent_path.relative_to(root).as_posix())
            if parent_name not in nodes:
                nodes[parent_name] = Node(name=parent_name, data=parent_data)

            nodes[parent_name].children.append(child_name)
            child_name = parent_name

    return nodes


def collate_datasets(root: Path) -> dict[str, dict[str, Any]]:
    """Collates all dataset entries into a single dictionary."""
    datasets_dir = root / DATASETS_REL_PATH
    return {k: asdict(v) for k, v in parse_nested_tree(datasets_dir, "dataset.yaml").items()}


def collate_tasks(root: Path) -> dict[str, dict[str, Any]]:
    """Collates all task entries into a single dictionary."""
    tasks_dir = root / TASKS_REL_PATH
    return {k: asdict(v) for k, v in parse_nested_tree(tasks_dir, "task.yaml").items()}


def collate_models(root: Path) -> dict[str, dict[str, Any]]:
    """Collates all model entries into a single dictionary."""
    models_dir = root / MODELS_REL_PATH
    return {k: asdict(v) for k, v in parse_nested_tree(models_dir, "model.yaml").items()}


def collate_entities(repo_dir: Path, output_dir: Path, do_overwrite: bool = False):
    """Collects all the information about datasets, tasks, and models in the repo and writes them to JSON.

    Args:
        repo_dir: The path to the MEDS_DEV repository.
        output_dir: The path to the output directory where the JSON files will be saved.

    Raises:
        FileNotFoundError: If the repository directory does not exist.
        NotADirectoryError: If the path is not a directory.
        FileExistsError: If the output directory already exists and do_overwrite is False.

    Examples:
        >>> test_disk = '''
        ... input_dir/src/MEDS_DEV:
        ...   datasets:
        ...     MIMIC:
        ...       README.md: "This is a README for the category."
        ...       III:
        ...         dataset.yaml: {"foo": "bar"}
        ...         README.md: "This is a README."
        ...         refs.bib: "@article{foo, bar}"
        ...         predicates.yaml: {"predicate": "value"}
        ...         requirements.txt: |-2
        ...           numpy==1.21.0
        ...           pandas==1.3.0
        ...       IV:
        ...         dataset.yaml: {"foo": "baz"}
        ...         README.md: "This is another README."
        ...         refs.bib: "@article{baz, qux}"
        ...         predicates.yaml: {"predicate": "alt_value"}
        ...         requirements.txt: |-2
        ...           numpy==1.21.0
        ...           pandas==1.3.0
        ...   tasks:
        ...     readmission:
        ...       30d:
        ...         README.md: "This is a README for the readmission/30d task."
        ...         task.yaml: {"task": "value"}
        ...   models:
        ...     cehrbert:
        ...       README.md: "This is a README for the model."
        ...       model.yaml: {"model": "value"}
        ...       refs.bib: "@article{model, paper}"
        ...       requirements.txt: "numpy==1.21.0"
        ... '''
        >>> with yaml_disk(test_disk) as root_dir:
        ...     input_dir = root_dir / "input_dir"
        ...     output_dir = root_dir / "output_dir"
        ...     collate_entities(input_dir, output_dir, do_overwrite=True)
        ...     print(f"Output contents:")
        ...     print_directory(output_dir)
        ...     print("------------")
        ...     print("Datasets:")
        ...     print(json.loads((output_dir / "datasets.json").read_text()))
        ...     print("Tasks:")
        ...     print(json.loads((output_dir / "tasks.json").read_text()))
        ...     print("Models:")
        ...     print(json.loads((output_dir / "models.json").read_text()))
        Output contents:
        ├── datasets.json
        ├── models.json
        └── tasks.json
        ------------
        Datasets:
        {'MIMIC/III': {'name': 'MIMIC/III',
                       'data': {'README.md': 'This is a README.',
                                'dataset.yaml': {'foo': 'bar'},
                                'predicates.yaml': {'predicate': 'value'},
                                'refs.bib': '@article{foo, bar}',
                                'requirements.txt': ['numpy==1.21.0', 'pandas==1.3.0']},
                                'children': []},
         'MIMIC': {'name': 'MIMIC',
                   'data': {'README.md': 'This is a README for the category.'},
                   'children': ['MIMIC/III', 'MIMIC/IV']},
         'MIMIC/IV': {'name': 'MIMIC/IV',
                      'data': {'README.md': 'This is another README.',
                               'dataset.yaml': {'foo': 'baz'},
                               'predicates.yaml': {'predicate': 'alt_value'},
                               'refs.bib': '@article{baz, qux}',
                               'requirements.txt': ['numpy==1.21.0', 'pandas==1.3.0']},
                               'children': []}}
        Tasks:
        {'readmission/30d': {'name': 'readmission/30d',
                             'data': {'README.md': 'This is a README for the readmission/30d task.',
                             'task.yaml': {'task': 'value'}},
                             'children': []}}
        Models:
        {'cehrbert': {'name': 'cehrbert',
                      'data': {'README.md': 'This is a README for the model.',
                               'model.yaml': {'model': 'value'},
                               'refs.bib': '@article{model, paper}',
                               'requirements.txt': ['numpy==1.21.0']},
                      'children': []}}

    Errors will be raised if the repository directory does not exist or is not a directory, or if the output
    filepaths exist and do_overwrite is False.

        >>> with yaml_disk(test_disk) as root_dir:
        ...     collate_entities(root_dir / "input_dir_not_real", "foo")
        Traceback (most recent call last):
            ...
        FileNotFoundError: Repository directory /tmp/tmp.../input_dir_not_real does not exist.
        >>> with yaml_disk(test_disk) as root_dir:
        ...     input_dir = root_dir / "input_dir" / "src" / "MEDS_DEV" / "models" / "cehrbert" / "README.md"
        ...     collate_entities(input_dir, "foo")
        Traceback (most recent call last):
            ...
        NotADirectoryError: Repository directory /tmp/tmp.../input_dir/src/MEDS_DEV/models/cehrbert/README.md
            is not a directory.
        >>> bad_outputs_disk = '''
        ...   input_dir:
        ...     README.md: "Repo README"
        ...   datasets.json: {"foo": "bar"}
        ... '''
        >>> with yaml_disk(bad_outputs_disk) as root_dir:
        ...     collate_entities(root_dir / "input_dir", root_dir, do_overwrite=False)
        Traceback (most recent call last):
            ...
        FileExistsError: Output filepath /tmp/tmp.../datasets.json already exists.
        >>> bad_outputs_disk = '''
        ... input_dir:
        ...   README.md: "Repo README"
        ... datasets.json/:
        ...   README.md: "Whoops this is now a directory"
        ... '''
        >>> with yaml_disk(bad_outputs_disk) as root_dir:
        ...     collate_entities(root_dir / "input_dir", root_dir, do_overwrite=True)
        Traceback (most recent call last):
            ...
        IsADirectoryError: Output filepath /tmp/tmp.../datasets.json is a directory.
    """

    if not repo_dir.exists():
        raise FileNotFoundError(f"Repository directory {repo_dir!s} does not exist.")
    if not repo_dir.is_dir():
        raise NotADirectoryError(f"Repository directory {repo_dir!s} is not a directory.")

    datasets_fp = output_dir / "datasets.json"
    tasks_fp = output_dir / "tasks.json"
    models_fp = output_dir / "models.json"

    for fp in [datasets_fp, tasks_fp, models_fp]:
        if fp.exists():
            if fp.is_dir():
                raise IsADirectoryError(f"Output filepath {fp!s} is a directory.")
            elif do_overwrite:
                fp.unlink()
            else:
                raise FileExistsError(f"Output filepath {fp!s} already exists.")

        fp.parent.mkdir(parents=True, exist_ok=True)

    datasets = collate_datasets(repo_dir)
    tasks = collate_tasks(repo_dir)
    models = collate_models(repo_dir)

    datasets_fp.write_text(json.dumps(datasets))
    tasks_fp.write_text(json.dumps(tasks))
    models_fp.write_text(json.dumps(models))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collate entities from the MEDS_DEV repository.")
    parser.add_argument("--repo_dir", type=Path, help="Path to the MEDS_DEV repository.")
    parser.add_argument("--output_dir", type=Path, help="Path to the output directory.")
    parser.add_argument(
        "--do_overwrite", action="store_true", default=False, help="Overwrite existing output files."
    )
    parser.add_argument(
        "--no_overwrite",
        action="store_false",
        dest="do_overwrite",
        help="Do not overwrite existing output files.",
    )
    args = parser.parse_args()

    collate_entities(args.repo_dir, args.output_dir, args.do_overwrite)
