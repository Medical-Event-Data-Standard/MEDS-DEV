"""Fast tests that every console-script module also runs via `python -m`.

Without an `if __name__ == "__main__"` guard, `python -m MEDS_DEV.<module>` imports the module and exits 0
having run nothing, so these check that `--help` actually prints the command's help text.
"""

import subprocess
import sys

import pytest


def run_module(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, check=False)


@pytest.mark.parametrize(
    ("args", "expected_help"),
    [
        (["MEDS_DEV.datasets"], "MEDS-DEV Dataset Builder Helper"),
        (["MEDS_DEV.tasks"], "MEDS-DEV Task Extractor Helper"),
        (["MEDS_DEV.models"], "MEDS-DEV Model Running Helper"),
        (["MEDS_DEV.evaluation"], "MEDS-DEV Evaluation Helper"),
        (["MEDS_DEV.results", "pack"], "MEDS-DEV Result Packager"),
        (["MEDS_DEV.results", "validate"], "MEDS-DEV Result Validator"),
        (["MEDS_DEV.web.collate_entities"], "Collate MEDS-DEV entity manifests"),
        (["MEDS_DEV.web.count_badges"], "Write shields.io badges counting MEDS-DEV entities"),
    ],
)
def test_module_runs_its_entrypoint(args: list[str], expected_help: str):
    out = run_module(*args, "--help")
    assert out.returncode == 0, out.stderr
    assert expected_help in out.stdout


@pytest.mark.parametrize("args", [["MEDS_DEV.results"], ["MEDS_DEV.results", "not_a_command"]])
def test_results_module_requires_a_command(args: list[str]):
    out = run_module(*args)
    assert out.returncode != 0
    assert "usage: python -m MEDS_DEV.results {pack,validate}" in out.stderr
