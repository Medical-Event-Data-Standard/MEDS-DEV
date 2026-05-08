"""Coverage for ``MEDS_DEV.web`` paths that aren't exercised by the in-module doctests.

The doctests in the web module cover the happy paths and the most common error paths. This file
fills in the rest: parse-error / error-threshold paths in ``aggregate_results``, the directory-type
errors in ``collate_entities``, and the ``main`` CLI entry points (which are tedious to exercise
from doctests but trivial to call with a monkeypatched ``sys.argv``).
"""

import json
import sys
from pathlib import Path

import pytest

from MEDS_DEV.web.aggregate_results import aggregate_results
from MEDS_DEV.web.aggregate_results import main as aggregate_main
from MEDS_DEV.web.collate_entities import collate_entities
from MEDS_DEV.web.collate_entities import main as collate_main

# ---------------------------------------------------------------------------
# aggregate_results: error paths
# ---------------------------------------------------------------------------


def test_aggregate_results_logs_and_skips_unparseable_blob(tmp_path: Path, caplog) -> None:
    """A single malformed result.json is logged but doesn't abort aggregation."""
    (tmp_path / "1").mkdir()
    (tmp_path / "1" / "result.json").write_text('{"valid": "json"}')
    (tmp_path / "2").mkdir()
    (tmp_path / "2" / "result.json").write_text("{not valid json")

    out = tmp_path / "all_results.json"
    with caplog.at_level("WARNING"):
        agg = aggregate_results(tmp_path, out)

    assert "1" in agg, "valid blob should be aggregated"
    assert "2" not in agg, "malformed blob should be skipped"
    assert any("Failed to read" in r.message for r in caplog.records)


def test_aggregate_results_aborts_when_error_threshold_exceeded(tmp_path: Path) -> None:
    """If parse errors exceed ``error_threshold``, aggregation raises."""
    for i in range(5):
        (tmp_path / str(i)).mkdir()
        (tmp_path / str(i) / "result.json").write_text("{not valid json")

    out = tmp_path / "all_results.json"
    with pytest.raises(ValueError, match="Too many parse errors"):
        aggregate_results(tmp_path, out, error_threshold=2)


# ---------------------------------------------------------------------------
# collate_entities: directory-type errors
# ---------------------------------------------------------------------------


def test_collate_entities_rejects_non_directory_repo(tmp_path: Path) -> None:
    """Passing a file path as ``repo_dir`` raises ``NotADirectoryError``."""
    file_as_repo = tmp_path / "not_a_dir"
    file_as_repo.write_text("just a file")
    with pytest.raises(NotADirectoryError, match="not a directory"):
        collate_entities(file_as_repo, tmp_path / "out", do_overwrite=True)


def test_collate_entities_rejects_directory_in_output_slot(tmp_path: Path) -> None:
    """If a target output path exists as a directory, raise even with do_overwrite=True."""
    repo = tmp_path / "repo"
    (repo / "src" / "MEDS_DEV" / "datasets" / "MIMIC-IV").mkdir(parents=True)
    (repo / "src" / "MEDS_DEV" / "datasets" / "MIMIC-IV" / "dataset.yaml").write_text(
        "metadata:\n  description: foo\n"
    )

    out = tmp_path / "out"
    out.mkdir()
    (out / "datasets.json").mkdir()  # collide with the file the collator wants to write

    with pytest.raises(IsADirectoryError, match="is a directory"):
        collate_entities(repo, out, do_overwrite=True)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def test_collate_main_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``meds-dev-collate-entities`` writes the three manifests to the output directory."""
    repo = tmp_path / "repo"
    (repo / "src" / "MEDS_DEV" / "datasets" / "MIMIC-IV").mkdir(parents=True)
    (repo / "src" / "MEDS_DEV" / "datasets" / "MIMIC-IV" / "dataset.yaml").write_text(
        "metadata:\n  description: foo\n"
    )
    (repo / "src" / "MEDS_DEV" / "tasks" / "mortality").mkdir(parents=True)
    (repo / "src" / "MEDS_DEV" / "tasks" / "mortality" / "first_24h.yaml").write_text("predicates: {a: b}\n")
    (repo / "src" / "MEDS_DEV" / "models" / "rp").mkdir(parents=True)
    (repo / "src" / "MEDS_DEV" / "models" / "rp" / "model.yaml").write_text("metadata:\n  description: rp\n")

    out = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meds-dev-collate-entities",
            "--repo_dir",
            str(repo),
            "--output_dir",
            str(out),
            "--do_overwrite",
        ],
    )
    collate_main()

    assert {p.name for p in out.iterdir()} == {"datasets.json", "tasks.json", "models.json"}
    datasets = json.loads((out / "datasets.json").read_text())
    assert "MIMIC-IV" in datasets


def test_aggregate_main_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``meds-dev-aggregate-results`` writes a populated all_results.json."""
    in_dir = tmp_path / "_results"
    in_dir.mkdir()
    (in_dir / "42").mkdir()
    (in_dir / "42" / "result.json").write_text('{"value": "from-cli"}')

    out = tmp_path / "all_results.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "meds-dev-aggregate-results",
            "--input_dir",
            str(in_dir),
            "--output_path",
            str(out),
        ],
    )
    aggregate_main()

    assert json.loads(out.read_text()) == {"42": {"value": "from-cli"}}
