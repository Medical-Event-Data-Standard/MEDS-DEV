import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import hydra
from omegaconf import DictConfig

from . import PACK_YAML, VALIDATE_YAML, Result, extract_result_dict_from_issue_body

logger = logging.getLogger(__name__)

MAX_SIZE_KB = 1.5


@hydra.main(version_base=None, config_path=str(PACK_YAML.parent), config_name=PACK_YAML.stem)
def pack_result(cfg: DictConfig):
    """Package the result of a MEDS-DEV experiment."""

    eval_fp = Path(cfg.evaluation_fp)
    if not eval_fp.is_file():
        raise FileNotFoundError(f"File not found: {eval_fp}")

    eval_result = json.loads(eval_fp.read_text())
    timestamp = datetime.fromtimestamp(eval_fp.stat().st_mtime, tz=UTC)

    result = Result(
        dataset=cfg.dataset,
        task=cfg.task,
        model=cfg.model,
        result=eval_result,
        timestamp=timestamp,
    )
    result.to_json(cfg.result_fp, do_overwrite=cfg.get("do_overwrite", False))


@hydra.main(
    version_base=None,
    config_path=str(VALIDATE_YAML.parent),
    config_name=VALIDATE_YAML.stem,
)
def validate_result(cfg: DictConfig):
    """Package the result of a MEDS-DEV experiment."""

    result_fp = Path(cfg.result_fp)

    if not result_fp.is_file():
        raise FileNotFoundError(f"File not found: {result_fp}")

    # File size check
    size_kb = result_fp.stat().st_size / 1024
    if size_kb > MAX_SIZE_KB:
        raise ValueError(f"Result file is too large ({size_kb:.2f} KB > {MAX_SIZE_KB} KB)")

    try:
        Result.from_json(result_fp)
    except Exception as e:
        raise ValueError("Result should be packaged and decodable") from e


def validate_result_from_issue() -> None:
    """Extract a fenced ``\\`\\`\\`json`` block from a GitHub issue body, validate, and write to disk.

    Used by ``upload_benchmark_result.yaml`` to collapse the previous extract-with-sed +
    validate-from-file flow into a single Python invocation. Reads the issue body from stdin (or
    from ``--issue_body_fp``), constructs a :class:`Result` (which validates via
    ``Result.__post_init__``), and writes the canonical JSON via :meth:`Result.to_json` (which
    sanitizes ``NaN`` / ``Inf`` to ``null``).
    """
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
        help="Path to a file containing the issue body text. If omitted, reads from stdin.",
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

    body = args.issue_body_fp.read_text() if args.issue_body_fp else sys.stdin.read()
    result_dict = extract_result_dict_from_issue_body(body)
    result = Result.from_dict(result_dict)  # validates via __post_init__
    result.to_json(args.result_fp, do_overwrite=args.do_overwrite)
    logger.info(f"Wrote validated result to {args.result_fp}")
