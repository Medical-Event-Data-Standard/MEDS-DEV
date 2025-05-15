#!/usr/bin/env python3

import json
from pathlib import Path
import logging
import argparse

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Aggregate results from multiple JSON files.")
    parser.add_argument(
        "--error-threshold",
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

    if not args.input_dir.exists():
        err_lines = ["Input directory '{args.input_dir.resolve()!s}' does not exist."]

        directories_to_check = [args.input_dir]
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
    if not args.input_dir.is_dir():
        raise NotADirectoryError(f"Input directory '{args.input_dir.resolve()!s}' is not a directory.")

    results = json.loads(args.output_path.read_text()).items() if args.output_path.exists() else {}

    result_fps = args.input_dir.glob("*/result.json")

    n_errors = 0
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
            n_errors += 1

            if n_errors > args.error_threshold:
                raise ValueError(
                    f"Too many errors ({n_errors}) while reading results. "
                    "Please check the logs for more details."
                ) from e

    if new_results == 0:
        all_jsons = list(args.input_dir.rglob("*.json"))
        raise ValueError(
            "Found no new results to add! Files present:\n"
            f"{', '.join([str(fp) for fp in result_fps])}.\n"
            f"All JSON files in input dir '{args.input_dir.resolve()!s}':\n"
            f"{', '.join([str(fp) for fp in all_jsons])}.\n"
        )

    # Write to a relative path so we can copy it to a different branch
    args.output_path.parent.mkdir(exist_ok=True)
    args.output_path.write_text(json.dumps(results))

    logger.info(f"Wrote {len(results)} results ({new_results} new) to {args.output_path}")


if __name__ == "__main__":
    main()
