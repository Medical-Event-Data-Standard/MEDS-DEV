"""Render every task's timeline figure and tables with Taskviz, for the MEDS-DEV website.

[Taskviz](https://github.com/rvandewater/Taskviz) draws an ACES task configuration as a timeline (trigger,
windows, prediction time, label window) and lists its windows and predicates as tables. It reads only the
task's YAML: no data and no ACES run are needed.

``regenerate_entities.yaml`` runs this on every push to ``main`` that touches a task and writes the output
to the ``_web`` orphan branch, next to the entity manifests:

- ``task_figures/<task name>/figure.svg``: follows the reader's light or dark system setting.
- ``task_figures/<task name>/figure-light.svg`` and ``figure-dark.svg``: one per theme, for sites that
  switch theme themselves (an ``<img>`` cannot see the page's theme).
- ``task_figures/<task name>/windows.md`` and ``predicates.md``: the tables, as Markdown.
- ``task_figures/index.json``: each task name mapped to its files, relative to ``task_figures/``.

``task_figures.yaml`` runs it on pull requests that add or change a task, so a task Taskviz cannot draw
fails there, and the figures can be downloaded from the run to review.

Taskviz is not a runtime dependency of MEDS-DEV (it is not on PyPI); it is in the ``dev`` dependency group
and is imported only when figures are rendered.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from .collate_entities import TASKS_REL_PATH

THEMES: dict[str, str] = {"figure.svg": "auto", "figure-light.svg": "light", "figure-dark.svg": "dark"}
TABLES: tuple[str, ...] = ("windows.md", "predicates.md")
INDEX_FILENAME = "index.json"


def find_tasks(repo_dir: Path) -> dict[str, Path]:
    """Find the task configurations in a MEDS-DEV repository, keyed by task name.

    The task name is the path from ``src/MEDS_DEV/tasks/`` without the ``.yaml`` suffix, as in the ``TASKS``
    registry.

    Examples:
        >>> tree = '''
        ... src/MEDS_DEV/tasks/:
        ...   README.md: Tasks
        ...   mortality/in_icu/first_24h.yaml: {predicates: {a: b}}
        ...   abnormal_lab/cbc/anemia/first_24h.yaml: {predicates: {c: d}}
        ... '''
        >>> with yaml_disk(tree) as repo:
        ...     {name: str(fp.relative_to(repo)) for name, fp in find_tasks(repo).items()}
        {'abnormal_lab/cbc/anemia/first_24h': 'src/MEDS_DEV/tasks/abnormal_lab/cbc/anemia/first_24h.yaml',
         'mortality/in_icu/first_24h': 'src/MEDS_DEV/tasks/mortality/in_icu/first_24h.yaml'}
        >>> with yaml_disk({"README.md": "empty repo"}) as repo:
        ...     find_tasks(repo)
        {}
    """
    tasks_dir = repo_dir / TASKS_REL_PATH
    return {
        fp.relative_to(tasks_dir).with_suffix("").as_posix(): fp for fp in sorted(tasks_dir.glob("**/*.yaml"))
    }


def render_task(config_fp: Path) -> dict[str, str]:
    """Render one task's figures and tables with Taskviz.

    Args:
        config_fp: Path to the task's ACES configuration file.

    Returns:
        The content of each output file, keyed by file name (see ``THEMES`` and ``TABLES``).

    Raises:
        ValueError: If Taskviz cannot draw the task.

    Examples:
        >>> task = {
        ...     "predicates": {"admission": "???", "death": {"code": {"regex": "MEDS_DEATH.*"}}},
        ...     "trigger": "admission",
        ...     "windows": {
        ...         "input": {"start": None, "end": "trigger + 24h", "index_timestamp": "end"},
        ...         "target": {"start": "input.end", "end": "start + 30d", "label": "death"},
        ...     },
        ... }
        >>> with yaml_disk({"task.yaml": task}) as d:
        ...     out = render_task(d / "task.yaml")
        >>> sorted(out)
        ['figure-dark.svg', 'figure-light.svg', 'figure.svg', 'predicates.md', 'windows.md']
        >>> out["figure.svg"].startswith("<svg")
        True
        >>> print(out["windows.md"].splitlines()[0])
        | Window | From | To | Requires | Role |

    A boundary Taskviz cannot place is an error:

        >>> bad_input = {**task["windows"]["input"], "end": "trigger + soon"}
        >>> bad = {**task, "windows": {**task["windows"], "input": bad_input}}
        >>> with yaml_disk({"task.yaml": bad}) as d:
        ...     render_task(d / "task.yaml")
        Traceback (most recent call last):
            ...
        ValueError: Taskviz cannot draw .../task.yaml.
    """
    import taskviz

    task = taskviz.read_task(config_fp)
    if not taskviz.can_draw(task):
        raise ValueError(f"Taskviz cannot draw {config_fp!s}.")

    out = {fn: taskviz.render_svg(task, theme=theme) for fn, theme in THEMES.items()}
    out["windows.md"] = taskviz.windows_table(task).to_markdown()
    out["predicates.md"] = taskviz.predicates_table(task).to_markdown()
    return out


def render_task_figures(
    repo_dir: Path,
    output_dir: Path,
    tasks: list[str] | None = None,
    do_overwrite: bool = False,
) -> dict[str, Any]:
    """Render the figures and tables of the tasks in ``repo_dir`` into ``output_dir``.

    Every selected task is attempted; if any fails, the others are still written and a ``ValueError`` naming
    all failures is raised afterwards.

    Args:
        repo_dir: Path to the MEDS-DEV repository (the directory containing ``src/MEDS_DEV/``).
        output_dir: Directory to write ``<task name>/...`` and ``index.json`` into. It is created if needed.
        tasks: Task names to render. ``None`` (default) renders every task.
        do_overwrite: If ``False`` (default) and an output file already exists, raise. If ``True``, overwrite.

    Returns:
        The index written to ``index.json``: each rendered task name mapped to its files.

    Raises:
        FileNotFoundError: If ``repo_dir`` does not exist.
        KeyError: If a name in ``tasks`` is not a task in ``repo_dir``.
        FileExistsError: If an output file exists and ``do_overwrite`` is ``False``.
        ValueError: If one or more tasks could not be rendered.

    Examples:
        >>> task = {
        ...     "predicates": {"admission": "???", "death": {"code": {"regex": "MEDS_DEATH.*"}}},
        ...     "trigger": "admission",
        ...     "windows": {
        ...         "input": {"start": None, "end": "trigger + 24h", "index_timestamp": "end"},
        ...         "target": {"start": "input.end", "end": "start + 30d", "label": "death"},
        ...     },
        ... }
        >>> tree = {"repo/src/MEDS_DEV/tasks/mortality/a.yaml": task,
        ...         "repo/src/MEDS_DEV/tasks/mortality/b.yaml": task}
        >>> with yaml_disk(tree) as d:
        ...     index = render_task_figures(d / "repo", d / "out")
        ...     print_directory(d / "out")
        ...     print(json.loads((d / "out" / "index.json").read_text())["mortality/a"]["figure"])
        ├── index.json
        └── mortality
            ├── a
            │   ├── figure-dark.svg
            │   ├── figure-light.svg
            │   ├── figure.svg
            │   ├── predicates.md
            │   └── windows.md
            └── b
                ├── figure-dark.svg
                ├── figure-light.svg
                ├── figure.svg
                ├── predicates.md
                └── windows.md
        mortality/a/figure.svg
        >>> index["mortality/b"]["figure_dark"]
        'mortality/b/figure-dark.svg'

    ``tasks`` selects a subset; an unknown name is an error:

        >>> with yaml_disk(tree) as d:
        ...     sorted(render_task_figures(d / "repo", d / "out", tasks=["mortality/b"]))
        ['mortality/b']
        >>> with yaml_disk(tree) as d:
        ...     render_task_figures(d / "repo", d / "out", tasks=["mortality/c"])
        Traceback (most recent call last):
            ...
        KeyError: "Unknown task(s): ['mortality/c']"

    Existing output needs ``do_overwrite=True``, and a task that cannot be drawn fails the run after the
    others are written:

        >>> with yaml_disk(tree) as d:
        ...     _ = render_task_figures(d / "repo", d / "out")
        ...     render_task_figures(d / "repo", d / "out")
        Traceback (most recent call last):
            ...
        FileExistsError: Output path ... already exists. Pass do_overwrite=True to replace.
        >>> bad_input = {**task["windows"]["input"], "end": "trigger + soon"}
        >>> bad = {**task, "windows": {**task["windows"], "input": bad_input}}
        >>> broken = {**tree, "repo/src/MEDS_DEV/tasks/mortality/a.yaml": bad}
        >>> with yaml_disk(broken) as d:
        ...     try:
        ...         render_task_figures(d / "repo", d / "out")
        ...     except ValueError as e:
        ...         print(e)
        ...     print(sorted(p.name for p in (d / "out" / "mortality").iterdir()))
        1 task(s) could not be rendered:
          mortality/a: Taskviz cannot draw .../a.yaml.
        ['b']
        >>> render_task_figures(Path("/nonexistent_path_xyz"), Path("/tmp"))
        Traceback (most recent call last):
            ...
        FileNotFoundError: Repository directory /nonexistent_path_xyz does not exist.
    """
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"Repository directory {repo_dir!s} does not exist.")

    all_tasks = find_tasks(repo_dir)
    if tasks is not None:
        unknown = sorted(set(tasks) - set(all_tasks))
        if unknown:
            raise KeyError(f"Unknown task(s): {unknown}")
        all_tasks = {name: fp for name, fp in all_tasks.items() if name in set(tasks)}

    index_fp = output_dir / INDEX_FILENAME
    targets = [index_fp] + [output_dir / name / fn for name in all_tasks for fn in (*THEMES, *TABLES)]
    existing = [fp for fp in targets if fp.exists()]
    if existing and not do_overwrite:
        fp = existing[0]
        raise FileExistsError(f"Output path {fp!s} already exists. Pass do_overwrite=True to replace.")

    index: dict[str, dict[str, str]] = {}
    failures: dict[str, str] = {}
    for name, config_fp in all_tasks.items():
        try:
            rendered = render_task(config_fp)
        except Exception as e:  # Any Taskviz error: report it with the others, below.
            failures[name] = str(e)
            continue
        task_dir = output_dir / name
        task_dir.mkdir(parents=True, exist_ok=True)
        for fn, content in rendered.items():
            (task_dir / fn).write_text(content)
        index[name] = {Path(fn).stem.replace("-", "_"): f"{name}/{fn}" for fn in rendered}

    output_dir.mkdir(parents=True, exist_ok=True)
    index_fp.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    if failures:
        lines = [f"  {name}: {msg}" for name, msg in failures.items()]
        raise ValueError(f"{len(failures)} task(s) could not be rendered:\n" + "\n".join(lines))
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Render MEDS-DEV task figures and tables with Taskviz.")
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
        help="Directory to write <task name>/figure*.svg, *.md and index.json into.",
    )
    parser.add_argument(
        "--tasks",
        nargs="*",
        default=None,
        help="Task names to render (default: every task).",
    )
    parser.add_argument(
        "--do_overwrite",
        action="store_true",
        help="Overwrite existing output files instead of raising.",
    )
    args = parser.parse_args()
    index = render_task_figures(args.repo_dir, args.output_dir, args.tasks, args.do_overwrite)
    print(json.dumps(sorted(index)))
