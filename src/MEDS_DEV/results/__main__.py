import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import hydra
from omegaconf import DictConfig

from . import CFG_YAML, Result

logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path=str(CFG_YAML.parent), config_name=CFG_YAML.stem)
def main(cfg: DictConfig):
    """Package the result of a MEDS-DEV experiment."""

    eval_fp = Path(cfg.evaluation_fp)
    if not eval_fp.is_file():
        raise FileNotFoundError(f"File not found: {eval_fp}")

    eval_result = json.loads(eval_fp.read_text())
    timestamp = datetime.fromtimestamp(eval_fp.stat().st_mtime, tz=timezone.utc)

    result = Result(
        dataset=cfg.dataset, task=cfg.task, model=cfg.model, result=eval_result, timestamp=timestamp
    )
    result.to_json(cfg.result_fp, do_overwrite=cfg.get("do_overwrite", False))
