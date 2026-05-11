"""Aggregate per-issue benchmark result JSON files into a single ``all_results.json`` blob.

Each benchmark submission lives at ``_results/<issue_number>/result.json`` on the ``_results`` orphan
branch. The MEDS-DEV website consumes a single aggregated file at ``_web/results/all_results.json``,
keyed by issue number.

Default behavior is append-only: existing keys in the output file are preserved as-is, and new keys
from the input directory are added. Each ``result.json`` represents one canonical experimental
result, so once a submission has been aggregated, re-running the aggregator should not silently
mutate that entry.

If a result.json's on-disk content has drifted from the aggregated entry (e.g., past corrupted run,
manual edit), the aggregator logs a loud warning but keeps the existing entry — silent drift is
worse than a noisy diagnostic. Pass ``do_overwrite=True`` (CLI: ``--do_overwrite``) to ignore the
existing aggregate and rebuild from scratch.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def aggregate_results(
    input_dir: Path,
    output_path: Path,
    error_threshold: int = 10,
    do_overwrite: bool = False,
) -> None:
    """Aggregate ``result.json`` files under ``input_dir`` into ``output_path``.

    The function is side-effecting: it writes the aggregated JSON to ``output_path`` and returns
    nothing. Callers (including doctests below) inspect the result by reading the file back.

    Args:
        input_dir: Directory whose subdirectories each contain a ``result.json``. The subdirectory
            name (typically a GitHub issue number) becomes the aggregate key.
        output_path: Path to write the aggregated JSON to.
        error_threshold: Maximum number of per-file parse failures tolerated before aborting.
        do_overwrite: If ``False`` (default) and ``output_path`` already exists, its existing
            entries are preserved as-is; only keys not present are added. If ``True``, the existing
            output is ignored and the aggregate is rebuilt from scratch.

    Raises:
        FileNotFoundError: If ``input_dir`` does not exist or contains no ``result.json`` files.
        NotADirectoryError: If ``input_dir`` is not a directory.
        ValueError: If parse failures exceed ``error_threshold``.

    Examples:
        The happy path — every result.json under input gets a corresponding key in the output:

        >>> tree = {
        ...     "44": {"result.json": {"result": "data 44"}},
        ...     "200": {"result.json": {"result": "data 200"}},
        ... }
        >>> with yaml_disk(tree) as d:
        ...     out = d / "all_results.json"
        ...     aggregate_results(d, out)
        ...     print(out.read_text())
        {
          "200": {
            "result": "data 200"
          },
          "44": {
            "result": "data 44"
          }
        }

        New keys are added on subsequent runs, but pre-existing keys are not refreshed. This is
        deliberate — each ``result.json`` is the canonical record for one experiment, and
        re-aggregation should not silently mutate already-canonical entries. If the on-disk
        ``result.json`` content has drifted from the aggregated entry, a loud warning is emitted
        but the existing entry is kept:

        >>> caplog.clear()
        >>> with caplog.at_level("WARNING", logger=__name__):
        ...   with yaml_disk({"1": {"result.json": {"result": "v1"}}}) as d:
        ...     out = d / "all_results.json"
        ...     aggregate_results(d, out)
        ...     # Mutate the source AND add a new issue:
        ...     _ = (d / "1" / "result.json").write_text('{"result": "v2"}')
        ...     _ = (d / "2").mkdir()
        ...     _ = (d / "2" / "result.json").write_text('{"result": "new"}')
        ...     aggregate_results(d, out)
        ...     print(json.loads(out.read_text()))
        {'1': {'result': 'v1'}, '2': {'result': 'new'}}
        >>> [r.message for r in caplog.records if "Content mismatch" in r.message]
        ['Content mismatch for issue 1: ... Keeping the existing aggregated entry; ...']

        Repeating the run with the source unchanged is a silent no-op apart from an info-level
        "already aggregated" log line per matching key:

        >>> caplog.clear()
        >>> with caplog.at_level("INFO", logger=__name__):
        ...   with yaml_disk({"1": {"result.json": {"result": "v1"}}}) as d:
        ...     out = d / "all_results.json"
        ...     aggregate_results(d, out)
        ...     aggregate_results(d, out)
        >>> [r.message for r in caplog.records if "already aggregated" in r.message]
        ['Skipping 1 (already aggregated)']

        When the on-disk source HAS legitimately changed (corrupted past run, manual edit to a
        result.json that should propagate), pass ``do_overwrite=True`` to rebuild from scratch:

        >>> with yaml_disk({"1": {"result.json": {"result": "v1"}}}) as d:
        ...     out = d / "all_results.json"
        ...     aggregate_results(d, out)
        ...     _ = (d / "1" / "result.json").write_text('{"result": "v2"}')
        ...     aggregate_results(d, out, do_overwrite=True)
        ...     json.loads(out.read_text())
        {'1': {'result': 'v2'}}

        A malformed ``result.json`` is logged at WARNING level and skipped; valid blobs in the same
        run are still aggregated:

        >>> caplog.clear()
        >>> with caplog.at_level("WARNING", logger=__name__):
        ...   with yaml_disk({"1": {"result.json": {"valid": "json"}}}) as d:
        ...     _ = (d / "2").mkdir()
        ...     _ = (d / "2" / "result.json").write_text("{not valid json")
        ...     out = d / "all_results.json"
        ...     aggregate_results(d, out)
        ...     print(json.loads(out.read_text()))
        {'1': {'valid': 'json'}}
        >>> any("Failed to read" in r.message for r in caplog.records)
        True

    Errors:

        >>> aggregate_results(Path("/nonexistent_xyz"), Path("/tmp/o.json"))
        Traceback (most recent call last):
            ...
        FileNotFoundError: Input directory ... does not exist.
        >>> with yaml_disk({"a.txt": "scalar"}) as d:
        ...     aggregate_results(d / "a.txt", d / "o.json")
        Traceback (most recent call last):
            ...
        NotADirectoryError: Input path ... is not a directory.
        >>> with yaml_disk({"no_results.txt": "unrelated"}) as d:
        ...     aggregate_results(d, d / "o.json")
        Traceback (most recent call last):
            ...
        FileNotFoundError: No result.json files found under ...

        Parse failures count toward ``error_threshold``; exceed it and aggregation aborts:

        >>> tree = {str(i): {"result.json": {"placeholder": True}} for i in range(5)}
        >>> with yaml_disk(tree) as d:
        ...     for i in range(5):
        ...         _ = (d / str(i) / "result.json").write_text("{not valid json")
        ...     aggregate_results(d, d / "o.json", error_threshold=2)
        Traceback (most recent call last):
            ...
        ValueError: Too many parse errors (3 > 2); aborting.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory {input_dir.resolve()!s} does not exist.")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path {input_dir.resolve()!s} is not a directory.")

    if do_overwrite or not output_path.exists():
        results: dict[str, Any] = {}
    else:
        results = json.loads(output_path.read_text())

    result_fps = sorted(input_dir.rglob("result.json"))
    if not result_fps:
        raise FileNotFoundError(f"No result.json files found under {input_dir.resolve()!s}.")

    parse_errors: list[str] = []
    new_results = 0
    for result_fp in result_fps:
        issue_num = result_fp.parent.name
        try:
            new_content = json.loads(result_fp.read_text())
        except (json.JSONDecodeError, OSError) as e:
            err = f"{result_fp}: {e}"
            logger.warning(f"Failed to read {err}")
            parse_errors.append(err)
            if len(parse_errors) > error_threshold:
                raise ValueError(
                    f"Too many parse errors ({len(parse_errors)} > {error_threshold}); aborting."
                ) from e
            continue

        if issue_num in results:
            if results[issue_num] != new_content:
                logger.warning(
                    f"Content mismatch for issue {issue_num}: aggregated entry in {output_path} "
                    f"does not match on-disk {result_fp}. Keeping the existing aggregated entry; "
                    f"pass do_overwrite=True to rebuild from scratch."
                )
            else:
                logger.info(f"Skipping {issue_num} (already aggregated)")
            continue

        results[issue_num] = new_content
        new_results += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True))
    logger.info(
        f"Wrote {len(results)} results ({new_results} new, {len(parse_errors)} errors) to {output_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate per-issue MEDS-DEV result JSON blobs.")
    parser.add_argument(
        "--input_dir",
        type=Path,
        default=Path("_results"),
        help="Directory containing <issue_number>/result.json subdirectories (default: _results).",
    )
    parser.add_argument(
        "--output_path",
        type=Path,
        default=Path("all_results.json"),
        help="Path to the aggregated JSON file (default: all_results.json).",
    )
    parser.add_argument(
        "--error_threshold",
        type=int,
        default=10,
        help="Max per-file parse failures before aborting (default: 10).",
    )
    parser.add_argument(
        "--do_overwrite",
        action="store_true",
        help=(
            "Ignore any existing output file and rebuild the aggregate from scratch. Default is "
            "append-only (existing keys preserved)."
        ),
    )
    args = parser.parse_args()
    aggregate_results(args.input_dir, args.output_path, args.error_threshold, args.do_overwrite)
