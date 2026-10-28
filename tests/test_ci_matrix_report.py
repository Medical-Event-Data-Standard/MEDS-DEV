"""Unit tests for the GitHub Actions compatibility report generator."""

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "ci_matrix_report.py"
SPEC = importlib.util.spec_from_file_location("ci_matrix_report", SCRIPT)
assert SPEC and SPEC.loader
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


def combo(model="meds_tab/tiny", dataset="MIMIC-IV", task="mortality/in_icu/first_24h"):
    return {"model": model, "dataset": dataset, "task": task}


def job(combination, conclusion="success", job_id=1):
    name = "full-integration ({model}, {dataset}, {task})".format(**combination)
    return {
        "name": name,
        "id": job_id,
        "html_url": f"https://github.com/example/repo/actions/runs/12/job/{job_id}",
        "conclusion": conclusion,
        "steps": [
            {"name": f"Run full test suite for {combination['model']}", "conclusion": conclusion}
        ],
    }


def make_report(combos, jobs):
    return reporter.build_report(combos, jobs, "example/repo", 12, 1, "deadbeef", "main")


def test_pass_fail_skip_and_missing_jobs():
    combos = [combo(), combo("cehrbert"), combo("genhpf"), combo("random_predictor")]
    jobs = [job(combos[0]), job(combos[1], "failure", 2), job(combos[2], "skipped", 3)]
    report = make_report(combos, jobs)
    assert [x["status"] for x in report["results"]] == [
        "passed", "failed", "skipped", "not_run"
    ]
    assert report["summary"]["total"] == 4
    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["skipped"] == 1
    assert report["summary"]["not_run"] == 1
    assert report["results"][0]["model"] == "meds_tab/tiny"
    assert report["results"][-1]["job_url"] is None
    assert "Full-integration compatibility matrix" in reporter.markdown(report)


def test_later_job_attempt_wins():
    c = combo()
    report = make_report([c], [job(c, "failure", 1), job(c, "success", 10)])
    assert report["results"][0]["status"] == "passed"
    assert report["results"][0]["job_id"] == 10


def test_failed_upload_is_distinguished_from_successful_pytest():
    c = combo()
    j = job(c, "failure")
    j["steps"][0]["conclusion"] = "success"
    report = make_report([c], [j])
    assert report["results"][0]["status"] == "failed"
    assert report["results"][0]["test_conclusion"] == "success"
