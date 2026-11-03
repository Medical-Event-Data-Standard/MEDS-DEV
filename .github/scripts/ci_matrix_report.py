"""Summarize full-integration GitHub Actions matrix jobs as JSON and Markdown.

The JSON is both an Actions artifact and the source of the public _web/ci/latest.json snapshot. Job
conclusions, rather than benchmark scores, determine the cell status.
"""

import json
import os
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

STATUSES = ("passed", "failed", "skipped", "cancelled", "not_run", "other")
CONCLUSIONS = {
    "success": "passed",
    "failure": "failed",
    "timed_out": "failed",
    "skipped": "skipped",
    "cancelled": "cancelled",
}


def fetch_jobs(repository: str, run_id: int, attempts: int = 4, backoff_seconds: float = 15) -> list[dict]:
    """Fetch *all* jobs, not just GitHub's default 30 or first 100.

    The jobs endpoint intermittently answers HTTP 502 for large matrix runs, which would fail the whole
    required check even though every test passed, so failed calls are retried with a linear backoff.
    """
    cmd = [
        "gh",
        "api",
        "--method",
        "GET",
        "--paginate",
        "--slurp",
        f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100",
    ]
    for attempt in range(1, attempts + 1):
        try:
            pages = json.loads(subprocess.check_output(cmd, text=True))
            break
        except subprocess.CalledProcessError:
            if attempt == attempts:
                raise
            time.sleep(backoff_seconds * attempt)
    return [job for page in pages for job in page["jobs"]]


def build_report(
    combos: list[dict],
    jobs: list[dict],
    repository: str,
    run_id: int,
    run_attempt: int,
    sha: str,
    branch: str,
) -> dict:
    if not combos:
        raise ValueError("Full integration produced no model/dataset/task combinations")

    # The combination name comes directly from GitHub Actions' matrix job naming.
    # Higher job IDs correspond to newer attempts in a re-run.
    by_name: dict[str, dict] = {}
    for job in jobs:
        name = job["name"]
        if name.startswith("full-integration (") and (name not in by_name or job["id"] > by_name[name]["id"]):
            by_name[name] = job

    results = []
    for combo in combos:
        model, dataset, task = (combo[k] for k in ("model", "dataset", "task"))
        name = f"full-integration ({model}, {dataset}, {task})"
        job = by_name.get(name)
        conclusion = job.get("conclusion") if job else None
        status = CONCLUSIONS.get(conclusion, "other") if job else "not_run"
        test_step = next(
            (
                step
                for step in (job or {}).get("steps", [])
                if step["name"].startswith("Run full test suite for ")
            ),
            None,
        )
        results.append(
            {
                "model": model,
                "dataset": dataset,
                "task": task,
                "status": status,
                "job_conclusion": conclusion,
                "test_conclusion": test_step.get("conclusion") if test_step else None,
                "job_id": job["id"] if job else None,
                "job_url": job.get("html_url") if job else None,
            }
        )

    counts = Counter(row["status"] for row in results)
    return {
        "schema_version": 1,
        "repository": repository,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
        "commit_sha": sha,
        "branch": branch,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "full-integration",
        "summary": {"total": len(results), **{key: counts[key] for key in STATUSES}},
        "results": results,
    }


def markdown(report: dict) -> str:
    def cell(value: str) -> str:
        return str(value).replace("|", r"\|").replace("\n", " ")

    s = report["summary"]
    lines = [
        "",
        "### Full-integration compatibility matrix",
        "",
        f"**{s['passed']}/{s['total']} passed** · "
        f"{s['failed']} failed · {s['skipped']} skipped · "
        f"{s['cancelled']} cancelled · {s['not_run']} not run · {s['other']} other",
        "",
        "Statuses are GitHub Actions **job conclusions**, not predictive-performance metrics. "
        "A passing job can still contain individually skipped pytest cases.",
        "",
        "| Model | Dataset | Task | Result | Details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        url = row["job_url"]
        details = f"[Logs]({url})" if url else "—"
        lines.append(
            f"| {cell(row['model'])} | {cell(row['dataset'])} | "
            f"{cell(row['task'])} | {row['status']} | {details} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    report = build_report(
        combos=json.loads(os.environ["EXPECTED_COMBOS_JSON"]),
        jobs=fetch_jobs(repository, run_id),
        repository=repository,
        run_id=run_id,
        run_attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
        sha=os.environ["GITHUB_SHA"],
        branch=os.environ["GITHUB_REF_NAME"],
    )
    destination = Path("ci-report/latest.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write(markdown(report))


if __name__ == "__main__":
    main()
