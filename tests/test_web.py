"""Coverage for ``MEDS_DEV.web`` paths that aren't exercised by the in-module doctests.

The doctests cover the happy paths and most of the error paths via :func:`yaml_to_disk.yaml_disk`.
This file fills in the rest: parse-error / error-threshold paths in ``aggregate_results``, the
directory-type errors in ``collate_entities``, and end-to-end CLI invocations via subprocess (so we
exercise the actual installed entry points, not just the Python ``main`` function).
"""

import json
import subprocess
from pathlib import Path

import pytest
from yaml_to_disk import yaml_disk

from MEDS_DEV.web.aggregate_results import aggregate_results
from MEDS_DEV.web.collate_entities import _walk_ancestors, collate_entities

# ---------------------------------------------------------------------------
# aggregate_results: error paths
# ---------------------------------------------------------------------------


def test_aggregate_results_logs_and_skips_unparseable_blob(caplog) -> None:
    """A single malformed result.json is logged but doesn't abort aggregation."""
    # yaml_disk's JSONFile validates+serializes dicts before writing, so it can't write a malformed
    # blob directly. Set up the directory structure with yaml_disk, then overwrite the malformed
    # entry as raw text.
    tree = {
        "1": {"result.json": {"valid": "json"}},
        "2": {"result.json": {"placeholder": True}},
    }
    with yaml_disk(tree) as d:
        (d / "2" / "result.json").write_text("{not valid json")
        with caplog.at_level("WARNING"):
            agg = aggregate_results(d, d / "all_results.json")

    assert "1" in agg, "valid blob should be aggregated"
    assert "2" not in agg, "malformed blob should be skipped"
    assert any("Failed to read" in r.message for r in caplog.records)


def test_aggregate_results_aborts_when_error_threshold_exceeded() -> None:
    """If parse errors exceed ``error_threshold``, aggregation raises."""
    tree = {str(i): {"result.json": {"placeholder": True}} for i in range(5)}
    with yaml_disk(tree) as d:
        for i in range(5):
            (d / str(i) / "result.json").write_text("{not valid json")
        with pytest.raises(ValueError, match="Too many parse errors"):
            aggregate_results(d, d / "all_results.json", error_threshold=2)


# ---------------------------------------------------------------------------
# collate_entities: directory-type errors
# ---------------------------------------------------------------------------


def test_collate_entities_rejects_non_directory_repo() -> None:
    """Passing a file path as ``repo_dir`` raises ``NotADirectoryError``."""
    with (
        yaml_disk({"not_a_dir.txt": "just a file"}) as d,
        pytest.raises(NotADirectoryError, match="not a directory"),
    ):
        collate_entities(d / "not_a_dir.txt", d / "out", do_overwrite=True)


def test_collate_entities_rejects_directory_in_output_slot() -> None:
    """If a target output path exists as a directory, raise even with do_overwrite=True."""
    tree = {
        "repo/src/MEDS_DEV/datasets/MIMIC-IV/dataset.yaml": {"metadata": {"description": "foo"}},
        # An existing directory at the spot the collator wants to write datasets.json.
        "out/datasets.json/": {".gitkeep": ""},
    }
    with yaml_disk(tree) as d, pytest.raises(IsADirectoryError, match="is a directory"):
        collate_entities(d / "repo", d / "out", do_overwrite=True)


# ---------------------------------------------------------------------------
# _walk_ancestors: filesystem-root defensive return
# ---------------------------------------------------------------------------


def test_walk_ancestors_terminates_when_leaf_is_not_under_root() -> None:
    """If ``leaf`` isn't actually under ``root``, the walk must stop at the filesystem root rather than loop
    forever.

    Triggers the ``parent == parent.parent`` guard.
    """
    ancestors = list(_walk_ancestors(Path("/some/leaf/path"), Path("/totally/different/tree")))
    # The yielded sequence ends at "/" once the guard fires.
    assert ancestors[-1] == Path("/")
    # And nothing under the bogus root is in the result.
    bogus_root = Path("/totally/different/tree")
    assert not any(bogus_root in a.parents or a == bogus_root for a in ancestors)


# ---------------------------------------------------------------------------
# CLI entry points (invoked as actual subprocesses against the installed package)
# ---------------------------------------------------------------------------


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
