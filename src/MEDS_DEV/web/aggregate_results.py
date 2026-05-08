"""Aggregate per-issue benchmark result JSON files into a single ``all_results.json`` blob.

Each benchmark submission lives at ``_results/<issue_number>/result.json`` on the ``_results`` orphan
branch. The MEDS-DEV website consumes a single aggregated file at ``_web/results/all_results.json``,
keyed by issue number.

This module produces that aggregate. If the output file already exists, existing entries are preserved
and only new issue numbers are added — making the script idempotent and append-only.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def aggregate_results(input_dir: Path, output_path: Path, error_threshold: int = 10) -> dict[str, Any]:
    """Aggregate ``result.json`` files under ``input_dir`` into ``output_path``.

    Args:
        input_dir: Directory whose subdirectories each contain a ``result.json``. The subdirectory
            name (typically a GitHub issue number) becomes the aggregate key.
        output_path: Path to write the aggregated JSON to. If the file already exists, its existing
            entries are preserved and only new keys are added.
        error_threshold: Maximum number of per-file parse failures tolerated before aborting.

    Returns:
        The full aggregated dict that was written.

    Raises:
        FileNotFoundError: If ``input_dir`` does not exist or contains no ``result.json`` files.
        NotADirectoryError: If ``input_dir`` is not a directory.
        ValueError: If parse failures exceed ``error_threshold``.

    Examples:
        >>> import json, tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     d = Path(d)
        ...     for issue in ("44", "200"):
        ...         (d / issue).mkdir()
        ...         _ = (d / issue / "result.json").write_text(json.dumps({"result": f"data {issue}"}))
        ...     out = d / "all_results.json"
        ...     agg = aggregate_results(d, out)
        ...     sorted(agg.keys())
        ['200', '44']
        >>> agg["44"]
        {'result': 'data 44'}

    A second call with the same input is a no-op (existing keys preserved, no new keys to add):

        >>> with tempfile.TemporaryDirectory() as d:
        ...     d = Path(d)
        ...     (d / "1").mkdir()
        ...     _ = (d / "1" / "result.json").write_text('{"result": "v1"}')
        ...     out = d / "all_results.json"
        ...     _ = aggregate_results(d, out)
        ...     # Now "modify" the source — aggregator should NOT re-read; it preserves existing.
        ...     _ = (d / "1" / "result.json").write_text('{"result": "v2"}')
        ...     agg = aggregate_results(d, out)
        ...     agg["1"]
        {'result': 'v1'}

    Errors:

        >>> aggregate_results(Path("/nonexistent_xyz"), Path("/tmp/o.json"))
        Traceback (most recent call last):
            ...
        FileNotFoundError: Input directory ... does not exist.
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile() as f:
        ...     aggregate_results(Path(f.name), Path("/tmp/o.json"))
        Traceback (most recent call last):
            ...
        NotADirectoryError: Input path ... is not a directory.
        >>> with tempfile.TemporaryDirectory() as d:
        ...     aggregate_results(Path(d), Path(d) / "o.json")
        Traceback (most recent call last):
            ...
        FileNotFoundError: No result.json files found under ...
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory {input_dir.resolve()!s} does not exist.")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path {input_dir.resolve()!s} is not a directory.")

    results: dict[str, Any] = json.loads(output_path.read_text()) if output_path.exists() else {}

    result_fps = sorted(input_dir.rglob("result.json"))
    if not result_fps:
        raise FileNotFoundError(f"No result.json files found under {input_dir.resolve()!s}.")

    parse_errors: list[str] = []
    new_results = 0
    for result_fp in result_fps:
        issue_num = result_fp.parent.name
        if issue_num in results:
            logger.info("Skipping %s (already aggregated)", issue_num)
            continue
        try:
            results[issue_num] = json.loads(result_fp.read_text())
            new_results += 1
        except (json.JSONDecodeError, OSError) as e:
            err = f"{result_fp}: {e}"
            logger.warning("Failed to read %s", err)
            parse_errors.append(err)
            if len(parse_errors) > error_threshold:
                raise ValueError(
                    f"Too many parse errors ({len(parse_errors)} > {error_threshold}); aborting."
                ) from e

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, sort_keys=True))
    logger.info(
        "Wrote %d results (%d new, %d errors) to %s",
        len(results),
        new_results,
        len(parse_errors),
        output_path,
    )
    return results


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
    args = parser.parse_args()
    aggregate_results(args.input_dir, args.output_path, args.error_threshold)


if __name__ == "__main__":
    main()
