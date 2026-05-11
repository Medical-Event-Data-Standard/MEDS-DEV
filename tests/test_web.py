"""End-to-end CLI tests for ``MEDS_DEV.web``.

The doctests in ``aggregate_results.py`` and ``collate_entities.py`` cover happy paths, error paths,
and the log-output contract (via the ``capture_log_to_stdout`` helper). This file is just the
subprocess-based CLI tests, which can't live in doctests without bloating them with shell setup.
"""

import json
import subprocess

from yaml_to_disk import yaml_disk


def test_collate_entities_cli() -> None:
    """``meds-dev-collate-entities`` writes the three manifests to the output directory."""
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
        datasets = json.loads((out / "datasets.json").read_text())
        assert "MIMIC-IV" in datasets


def test_aggregate_results_cli() -> None:
    """``meds-dev-aggregate-results`` writes a populated all_results.json."""
    tree = {"_results/42/result.json": {"value": "from-cli"}}
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
        assert json.loads(out.read_text()) == {"42": {"value": "from-cli"}}
