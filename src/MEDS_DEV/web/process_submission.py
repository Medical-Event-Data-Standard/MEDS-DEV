"""Process a GitHub issue benchmark-result submission.

Drives the ``upload_benchmark_result.yaml`` workflow's per-submission step: read the issue body,
extract the fenced ``\\`\\`\\`json`` block, validate it against :class:`MEDS_DEV.results.Result`, and
write the canonical (NaN-sanitized) JSON to disk for the workflow to commit to the ``_results``
branch.

The CLI (``meds-dev-process-submission``) accepts the issue body via (in priority order):

1. ``--issue_body_fp <path>`` — read from a file.
2. ``$ISSUE_BODY`` environment variable (override the name with ``--issue_body_env_var``).
3. Stdin — if neither of the above is provided.

The GitHub Actions workflow uses option 2 because routing untrusted issue body content through an
env var avoids shell-injection. Option 3 is for ad-hoc local invocation (``cat body.txt | meds-dev-
process-submission ...``); option 1 is for tooling that already has the body on disk.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from ..results import Result

JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def extract_result_dict_from_issue_body(body: str) -> dict[str, Any]:
    '''Extract the first fenced ```json ... ``` block from a GitHub issue body.

    The benchmark-result submission template asks contributors to paste a JSON blob inside a fenced
    code block. This helper returns the parsed dict so a caller can hand it to
    :meth:`MEDS_DEV.results.Result.from_dict` for validation.

    Raises:
        ValueError: If no fenced ```json``` block is found, or if the block isn't valid JSON.

    Examples:
        Happy path — the helper plucks out the dict regardless of surrounding prose:

        >>> body = """Hi, here's my result:
        ...
        ... ```json
        ... {"dataset": "MIMIC-IV", "result": {"acc": 0.5}}
        ... ```
        ...
        ... Thanks!"""
        >>> extract_result_dict_from_issue_body(body)
        {'dataset': 'MIMIC-IV', 'result': {'acc': 0.5}}

        Multi-line JSON inside the block works:

        >>> body = """
        ... ```json
        ... {
        ...   "dataset": "MIMIC-IV",
        ...   "result": {"acc": 0.5}
        ... }
        ... ```
        ... """
        >>> extract_result_dict_from_issue_body(body)
        {'dataset': 'MIMIC-IV', 'result': {'acc': 0.5}}

        Missing block:

        >>> extract_result_dict_from_issue_body("no fenced block here")
        Traceback (most recent call last):
            ...
        ValueError: No ```json``` fenced block found in issue body.

        Malformed JSON inside the block:

        >>> extract_result_dict_from_issue_body("""
        ... ```json
        ... {not valid json
        ... ```
        ... """)
        Traceback (most recent call last):
            ...
        ValueError: Issue body's ```json``` block is not valid JSON: ...
    '''
    match = JSON_BLOCK_RE.search(body)
    if match is None:
        raise ValueError("No ```json``` fenced block found in issue body.")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"Issue body's ```json``` block is not valid JSON: {e}") from e


def process_submission(body: str, result_fp: Path, do_overwrite: bool = False) -> None:
    """Extract a result from an issue body, validate it, and write the canonical JSON to disk."""
    result_dict = extract_result_dict_from_issue_body(body)
    result = Result.from_dict(result_dict)  # validates via __post_init__
    result.to_json(result_fp, do_overwrite=do_overwrite)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a ```json``` block from a GitHub issue body, validate it as a MEDS-DEV "
            "result, and write the validated JSON to a file."
        ),
    )
    parser.add_argument(
        "--issue_body_fp",
        type=Path,
        default=None,
        help="Path to a file containing the issue body text. Takes priority over env-var / stdin.",
    )
    parser.add_argument(
        "--issue_body_env_var",
        default="ISSUE_BODY",
        help=(
            "Name of the environment variable to read the issue body from when --issue_body_fp is "
            "not set. Defaults to ISSUE_BODY (the GHA convention)."
        ),
    )
    parser.add_argument(
        "--result_fp",
        type=Path,
        required=True,
        help="Path to write the validated result JSON to.",
    )
    parser.add_argument(
        "--do_overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    args = parser.parse_args()

    if args.issue_body_fp is not None:
        body = args.issue_body_fp.read_text()
    elif (env_val := os.environ.get(args.issue_body_env_var)) is not None:
        body = env_val
    elif not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        parser.error(
            f"No issue body provided. Pass --issue_body_fp, set ${args.issue_body_env_var}, "
            "or pipe the body on stdin."
        )

    process_submission(body, args.result_fp, do_overwrite=args.do_overwrite)
