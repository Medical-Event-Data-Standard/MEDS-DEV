import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import hydra
from omegaconf import DictConfig

from . import PACK_YAML, VALIDATE_YAML, Result

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


if __name__ == "__main__":  # pragma: no cover
    # This module hosts two entry points, so `python -m MEDS_DEV.results` takes the command name first, e.g.
    # `python -m MEDS_DEV.results validate result_fp=...`; the remaining arguments go to that command.
    commands = {"pack": pack_result, "validate": validate_result}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        sys.exit(f"usage: python -m MEDS_DEV.results {{{','.join(commands)}}} [OVERRIDES...]")
    commands[sys.argv.pop(1)]()
