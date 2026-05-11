"""End-to-end CLI tests for ``MEDS_DEV.web``.

The doctests in ``aggregate_results.py`` and ``collate_entities.py`` cover happy paths, error paths,
and the log-output contract (via pytest's ``caplog`` fixture, injected into the doctest namespace).
This file is just the subprocess-based CLI tests, which can't live in doctests without bloating
them with shell setup.
"""

import json
import subprocess

from yaml_to_disk import yaml_disk


def test_collate_entities_cli() -> None:
    """``meds-dev-collate-entities`` writes the three manifests; their contents match the source tree
    deterministically."""
    tree = {
        "repo/src/MEDS_DEV/": {
            "datasets/MIMIC-IV/dataset.yaml": {"metadata": {"description": "foo"}},
            "tasks/mortality/first_24h.yaml": {"predicates": {"a": "b"}},
            "models/rp/model.yaml": {"metadata": {"description": "rp"}},
        }
    }
    with yaml_disk(tree) as d:
        out = d / "out"
        result = subprocess.run(
            [
                "meds-dev-collate-entities",
                "--repo_dir",
                str(d / "repo"),
                "--output_dir",
                str(out),
                "--do_overwrite",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert {p.name for p in out.iterdir()} == {"datasets.json", "tasks.json", "models.json"}

        assert json.loads((out / "datasets.json").read_text()) == {
            "MIMIC-IV": {
                "name": "MIMIC-IV",
                "data": {"type": "dataset", "entity": {"metadata": {"description": "foo"}}},
                "children": [],
            }
        }
        assert json.loads((out / "tasks.json").read_text()) == {
            "mortality/first_24h": {
                "name": "mortality/first_24h",
                "data": {"type": "task", "entity": {"predicates": {"a": "b"}}},
                "children": [],
            }
        }
        assert json.loads((out / "models.json").read_text()) == {
            "rp": {
                "name": "rp",
                "data": {"type": "model", "entity": {"metadata": {"description": "rp"}}},
                "children": [],
            }
        }


def test_aggregate_results_cli() -> None:
    """``meds-dev-aggregate-results`` writes all results to a single aggregated file."""
    tree = {
        "_results/": {
            "42/result.json": {"model": "a", "score": 0.91},
            "43/result.json": {"model": "b", "score": 0.85},
            "44/result.json": {"model": "c", "score": 0.78},
        }
    }
    with yaml_disk(tree) as d:
        out = d / "all_results.json"
        result = subprocess.run(
            [
                "meds-dev-aggregate-results",
                "--input_dir",
                str(d / "_results"),
                "--output_path",
                str(out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert json.loads(out.read_text()) == {
            "42": {"model": "a", "score": 0.91},
            "43": {"model": "b", "score": 0.85},
            "44": {"model": "c", "score": 0.78},
        }
