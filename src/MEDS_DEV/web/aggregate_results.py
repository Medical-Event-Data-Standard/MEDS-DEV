#!/usr/bin/env python3

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def aggregate_results(input_dir: Path, output_path: Path, error_threshold: int = 10) -> None:
    """Aggregate results from multiple result JSON blurbs into a single JSON file.

    Args:
        input_dir: Directory containing the result JSON files.
        output_path: Path to the output JSON file.
        error_threshold: Maximum number of errors before stopping the aggregation process.

    Raises:
        FileNotFoundError: If the input directory does not exist or is not a directory.
        NotADirectoryError: If the input path is not a directory.
        ValueError: If too many errors occur while reading the result files.

    Examples:
        >>> with yaml_disk('''
        ...   _results:
        ...     "44":
        ...       result.json: {"result": "data for 44"}
        ...     "200":
        ...       result.json: {"result": "data for 200"}
        ... ''') as root_dir:
        ...     output_path = root_dir / "_all_results.json"
        ...     aggregate_results(root_dir / "_results", output_path)
        ...     print(output_path.read_text())
        {"44": {"result": "data for 44"}, "200": {"result": "data for 200"}}
    """
    if not input_dir.exists():
        err_lines = [f"Input directory '{input_dir.resolve()!s}' does not exist."]

        directories_to_check = [input_dir]
        while len(directories_to_check) < 3:
            new_dir = directories_to_check[-1].parent
            if not new_dir.exists():
                err_lines.append(f"Parent directory '{new_dir.resolve()!s}' does not exist.")
                directories_to_check.append(new_dir)
            else:
                err_lines.append(f"Parent directory '{new_dir.resolve()!s}' exists.")
                for child in new_dir.iterdir():
                    err_lines.append(f"  contains '{child.name}'")
                break

        raise FileNotFoundError("\n".join(err_lines))
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory '{input_dir.resolve()!s}' is not a directory.")

    results = json.loads(output_path.read_text()) if output_path.exists() else {}

    result_fps = list(input_dir.rglob("result.json"))

    no_results_err_lines = [
        f"Found no new results to add! Files present: {', '.join([str(fp) for fp in result_fps])}."
    ]

    if not result_fps:
        all_jsons = list(input_dir.rglob("*.json"))
        missing_files_err_lines = [
            *no_results_err_lines,
            f"All JSON files in input dir '{input_dir.resolve()!s}':"
            f"{', '.join([str(fp) for fp in all_jsons])}.",
        ]
        raise FileNotFoundError("\n".join(missing_files_err_lines))

    parse_errors = []
    new_results = 0
    for result_fp in result_fps:
        issue_num = result_fp.parent.name

        if issue_num in results:
            logger.info(f"Skipping {result_fp.parent.name} as it is already in the aggregated results")
            continue

        try:
            results[issue_num] = json.loads(result_fp.read_text())
            new_results += 1
        except Exception as e:
            logger.warning(f"Failed to read {result_fp}: {e}")
            parse_errors.append(str(e))

            if len(parse_errors) > error_threshold:
                raise ValueError(
                    f"Too many errors ({len(parse_errors)}) while reading results. "
                    "Please check the logs for more details."
                ) from e

    if new_results == 0:
        all_jsons = list(input_dir.rglob("*.json"))
        err_lines = [*no_results_err_lines, f"Obtained {len(parse_errors)} errors: ", *parse_errors]
        raise ValueError("\n".join(err_lines))

    # Write to a relative path so we can copy it to a different branch
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(results))

    logger.info(f"Wrote {len(results)} results ({new_results} new) to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate results from multiple JSON files.")
    parser.add_argument(
        "--error_threshold",
        type=int,
        default=10,
        help="Maximum number of errors before stopping the aggregation process (default 10).",
    )
    parser.add_argument(
        "--output_path",
        type=Path,
        default=Path("_all_results.json"),
        help="Path to the output JSON file (default _all_results.json).",
    )
    parser.add_argument(
        "--input_dir",
        type=Path,
        default=Path("_results"),
        help="Directory containing the result JSON files (default _results).",
    )

    args = parser.parse_args()

    aggregate_results(args.input_dir, args.output_path, args.error_threshold)
