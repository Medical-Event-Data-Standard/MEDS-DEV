"""End-to-end CLI tests for ``MEDS_DEV.web``.

The doctests in ``aggregate_results.py`` and ``collate_entities.py`` cover happy paths, error paths,
and the log-output contract (via pytest's ``caplog`` fixture, injected into the doctest namespace).
This file is just the subprocess-based CLI tests, which can't live in doctests without bloating
them with shell setup.
"""

import json
import subprocess
import sys

import pytest
from yaml_to_disk import yaml_disk

ISSUE_BODY = """Hi! Here's my result.

```json
{
  "dataset": "MIMIC-IV",
  "task": "mortality/in_icu/first_24h",
  "model": "random_predictor",
  "timestamp": "2025-01-01T00:00:00",
  "result": {"acc": 0.85, "auc": NaN},
  "version": "v0.1.0"
}
```

Thanks!"""


def _assert_canonical_result_written(out_fp) -> None:
    """Shared assertions for the three body-source variants below."""
    written = json.loads(out_fp.read_text())
    assert written["dataset"] == "MIMIC-IV"
    assert written["task"] == "mortality/in_icu/first_24h"
    assert written["model"] == "random_predictor"
    # NaN is sanitized to None on the way through Result.to_json:
    assert written["result"] == {"acc": 0.85, "auc": None}
    # On-disk JSON is strict (no bare NaN tokens):
    assert "NaN" not in out_fp.read_text()


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


def test_process_submission_cli_issue_body_arg() -> None:
    """``--issue_body`` (direct string): extract → validate → canonical JSON."""
    with yaml_disk({".gitkeep": ""}) as d:
        out = d / "result.json"
        subprocess.run(
            [
                "meds-dev-process-submission",
                "--issue_body",
                ISSUE_BODY,
                "--result_fp",
                str(out),
                "--do_overwrite",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert_canonical_result_written(out)


def test_process_submission_cli_issue_body_fp() -> None:
    """``--issue_body_fp``: read body from a file, then extract → validate → canonical JSON."""
    with yaml_disk({"body.md": ISSUE_BODY}) as d:
        out = d / "result.json"
        subprocess.run(
            [
                "meds-dev-process-submission",
                "--issue_body_fp",
                str(d / "body.md"),
                "--result_fp",
                str(out),
                "--do_overwrite",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _assert_canonical_result_written(out)


def test_process_submission_cli_stdin() -> None:
    """Stdin fallback: with no body flag, the CLI reads the body from stdin when it is piped."""
    with yaml_disk({".gitkeep": ""}) as d:
        out = d / "result.json"
        subprocess.run(
            ["meds-dev-process-submission", "--result_fp", str(out), "--do_overwrite"],
            input=ISSUE_BODY,
            check=True,
            capture_output=True,
            text=True,
        )
        _assert_canonical_result_written(out)


def test_process_submission_main_errors_without_body(monkeypatch, tmp_path) -> None:
    """No body flag + stdin attached to a tty → ``parser.error`` and ``SystemExit``."""
    from MEDS_DEV.web.process_submission import main

    monkeypatch.setattr(
        sys, "argv", ["meds-dev-process-submission", "--result_fp", str(tmp_path / "out.json")]
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with pytest.raises(SystemExit):
        main()
