"""Behavioral tests for ``MEDS_DEV.web`` that don't fit cleanly as doctests.

The doctests in ``aggregate_results.py`` and ``collate_entities.py`` cover the happy paths and
file-system error paths (``yaml_disk`` makes those concise). The tests below are the ones whose
assertions don't fit comfortably in a doctest:

- Logger assertions (``caplog``) for the parse-error / skip / mismatch paths.
- End-to-end CLI invocations through ``subprocess.run`` against the installed entry points.
"""

import json
import subprocess

from yaml_to_disk import yaml_disk

from MEDS_DEV.web.aggregate_results import aggregate_results


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
        out = d / "all_results.json"
        with caplog.at_level("WARNING"):
            aggregate_results(d, out)
        agg = json.loads(out.read_text())

    assert "1" in agg, "valid blob should be aggregated"
    assert "2" not in agg, "malformed blob should be skipped"
    assert any("Failed to read" in r.message for r in caplog.records)


def test_aggregate_results_skip_logs_when_content_matches(caplog) -> None:
    """When an existing aggregated entry matches the on-disk result.json, log info-level skip (no warning, no
    work)."""
    with yaml_disk({"1": {"result.json": {"result": "v1"}}}) as d:
        out = d / "all_results.json"
        aggregate_results(d, out)  # writes v1
        with caplog.at_level("INFO"):
            aggregate_results(d, out)  # second call: same data on disk
        agg = json.loads(out.read_text())
    assert agg["1"] == {"result": "v1"}
    skip_logs = [r for r in caplog.records if "already aggregated" in r.message]
    assert skip_logs, "expected an info-level skip log"
    assert not any("Content mismatch" in r.message for r in caplog.records)


def test_aggregate_results_warns_on_content_mismatch(caplog) -> None:
    """When an existing aggregated entry differs from the on-disk result.json, log a loud warning and keep the
    existing entry (do not silently overwrite)."""
    with yaml_disk({"1": {"result.json": {"result": "v1"}}}) as d:
        out = d / "all_results.json"
        # First aggregation: writes v1 to the output.
        aggregate_results(d, out)
        # Mutate the on-disk result.json so it no longer matches the aggregated entry.
        (d / "1" / "result.json").write_text('{"result": "v2"}')

        with caplog.at_level("WARNING"):
            aggregate_results(d, out)
        agg = json.loads(out.read_text())

    # Existing aggregated entry is kept; on-disk drift does not propagate.
    assert agg["1"] == {"result": "v1"}
    # ...but a clear warning is emitted naming the affected issue.
    mismatch_warnings = [r for r in caplog.records if "Content mismatch" in r.message]
    assert mismatch_warnings, "expected a content-mismatch warning"
    assert "issue 1" in mismatch_warnings[0].message


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
