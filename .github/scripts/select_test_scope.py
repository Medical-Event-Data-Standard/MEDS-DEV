#!/usr/bin/env python3
"""Determine which CI test lanes to run based on changed files.

Usage:
    python select_test_scope.py <base_ref> <head_ref>

Outputs GitHub Actions outputs via $GITHUB_OUTPUT (or prints to stdout if not set).
"""

import json
import os
import re
import subprocess
import sys


def get_changed_files(base_ref: str, head_ref: str) -> list[str]:
    """Return list of files changed between base_ref and head_ref."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


# Patterns for files that are docs/metadata only and never affect test outcomes.
DOCS_ONLY_PATTERNS = [
    r"^README\.md$",
    r"^docs/",
    r"^templates/",
    r"^\.github/ISSUE_TEMPLATE/",
    r"^refs\.bib$",
    r"^LICENSE$",
    r"^\.gitignore$",
]

# Patterns for shared/core files that should trigger a full run.
CORE_PATTERNS = [
    r"^src/MEDS_DEV/__init__\.py$",
    r"^src/MEDS_DEV/utils\.py$",
    r"^src/MEDS_DEV/configs/",
    r"^src/MEDS_DEV/evaluation/",
    r"^src/MEDS_DEV/results/",
    r"^src/MEDS_DEV/datasets/__init__\.py$",
    r"^src/MEDS_DEV/datasets/__main__\.py$",
    r"^src/MEDS_DEV/tasks/__init__\.py$",
    r"^src/MEDS_DEV/tasks/__main__\.py$",
    r"^src/MEDS_DEV/models/__init__\.py$",
    r"^src/MEDS_DEV/models/__main__\.py$",
    r"^tests/conftest\.py$",
    r"^tests/utils\.py$",
    r"^pyproject\.toml$",
    r"^uv\.lock$",
    r"^\.github/workflows/",
    r"^\.github/actions/",
    r"^\.github/scripts/",
]

# Component-scoped patterns
DATASET_PATTERN = re.compile(r"^src/MEDS_DEV/datasets/([^/]+)/")
TASK_PATTERN = re.compile(r"^src/MEDS_DEV/tasks/(.+)\.yaml$")
MODEL_PATTERN = re.compile(r"^src/MEDS_DEV/models/(.+?)/[^/]+$")

# Test file patterns that map to specific lanes
TEST_DATASET_PATTERN = re.compile(r"^tests/test_0_datasets\.py$")
TEST_TASK_PATTERN = re.compile(r"^tests/test_1_tasks\.py$")
TEST_MODEL_PATTERNS = [
    re.compile(r"^tests/test_1_unsupervised_models\.py$"),
    re.compile(r"^tests/test_2_supervised_models\.py$"),
]
TEST_EVAL_PATTERN = re.compile(r"^tests/test_3_evaluation\.py$")
TEST_PACKAGING_PATTERN = re.compile(r"^tests/test_4_result_packaging\.py$")


def classify_changes(changed_files: list[str]) -> dict:
    """Classify changed files into test scope decisions."""
    changed_datasets: set[str] = set()
    changed_tasks: set[str] = set()
    changed_models: set[str] = set()
    run_full = False
    is_docs_only = True
    reasons: list[str] = []

    for filepath in changed_files:
        # Check docs-only
        is_doc = any(re.match(p, filepath) for p in DOCS_ONLY_PATTERNS)

        if not is_doc:
            is_docs_only = False

        # Check core patterns → promote to full
        if any(re.match(p, filepath) for p in CORE_PATTERNS):
            run_full = True
            reasons.append(f"core file changed: {filepath}")
            continue

        if is_doc:
            continue

        # Check dataset-scoped
        m = DATASET_PATTERN.match(filepath)
        if m:
            changed_datasets.add(m.group(1))
            continue

        # Check task-scoped — resolve to logical task name (slash-separated, no .yaml)
        m = TASK_PATTERN.match(filepath)
        if m:
            task_name = m.group(1)
            # Strip leading path component that is the tasks package itself
            changed_tasks.add(task_name)
            continue

        # Check model-scoped
        m = MODEL_PATTERN.match(filepath)
        if m:
            changed_models.add(m.group(1))
            continue

        # Test file changes — map to appropriate lane or promote to full
        if TEST_DATASET_PATTERN.match(filepath):
            run_full = True
            reasons.append(f"dataset test file changed: {filepath}")
        elif TEST_TASK_PATTERN.match(filepath):
            run_full = True
            reasons.append(f"task test file changed: {filepath}")
        elif any(p.match(filepath) for p in TEST_MODEL_PATTERNS):
            run_full = True
            reasons.append(f"model test file changed: {filepath}")
        elif TEST_EVAL_PATTERN.match(filepath) or TEST_PACKAGING_PATTERN.match(filepath):
            run_full = True
            reasons.append(f"evaluation/packaging test changed: {filepath}")
        elif filepath.startswith("tests/"):
            # Any other test file change (e.g., test_registry_validation.py) → just fast checks
            reasons.append(f"non-integration test file changed: {filepath}")
        else:
            # Unknown file — conservative: promote to full
            run_full = True
            reasons.append(f"unclassified file changed: {filepath}")

    if not changed_files:
        is_docs_only = False
        run_full = True
        reasons.append("no changed files detected — running full")

    return {
        "run_full": run_full,
        "docs_only": is_docs_only and not run_full,
        "changed_datasets": sorted(changed_datasets),
        "changed_tasks": sorted(changed_tasks),
        "changed_models": sorted(changed_models),
        "reason": "; ".join(reasons) if reasons else "component-scoped changes only",
    }


def set_output(name: str, value: str):
    """Write a GitHub Actions output variable."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <base_ref> <head_ref>", file=sys.stderr)
        sys.exit(1)

    base_ref = sys.argv[1]
    head_ref = sys.argv[2]

    changed_files = get_changed_files(base_ref, head_ref)
    scope = classify_changes(changed_files)

    set_output("run_full", json.dumps(scope["run_full"]))
    set_output("docs_only", json.dumps(scope["docs_only"]))
    set_output("changed_datasets", json.dumps(scope["changed_datasets"]))
    set_output("changed_tasks", json.dumps(scope["changed_tasks"]))
    set_output("changed_models", json.dumps(scope["changed_models"]))
    set_output("reason", scope["reason"])

    # Print summary to CI logs
    print(f"Changed files ({len(changed_files)}):")
    for f in changed_files:
        print(f"  {f}")
    print("\nScope decision:")
    print(f"  run_full: {scope['run_full']}")
    print(f"  docs_only: {scope['docs_only']}")
    print(f"  changed_datasets: {scope['changed_datasets']}")
    print(f"  changed_tasks: {scope['changed_tasks']}")
    print(f"  changed_models: {scope['changed_models']}")
    print(f"  reason: {scope['reason']}")


if __name__ == "__main__":
    main()
