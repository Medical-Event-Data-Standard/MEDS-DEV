import logging
import shutil
from pathlib import Path

import hydra
from omegaconf import DictConfig

from ..utils import run_in_env, temp_env
from . import CFG_YAML, MODELS, model_commands

logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path=str(CFG_YAML.parent), config_name=CFG_YAML.stem)
def main(cfg: DictConfig):
    if cfg.model not in MODELS:
        raise ValueError(f"Model {cfg.model} not currently configured. Available models: {MODELS.keys()}")

    commands = MODELS[cfg.model]["commands"]
    model_dir = MODELS[cfg.model]["model_dir"]
    requirements = MODELS[cfg.model]["requirements"]

    output_dir = Path(cfg.output_dir)
    if cfg.get("do_overwrite", False) and output_dir.exists():  # pragma: no cover
        logger.info(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    with temp_env(cfg, requirements) as (temp_dir, env):
        for cmd, out_dir in model_commands(cfg, commands, model_dir):
            logger.info(f"Considering running model command: {cmd}")
            try:
                run_in_env(cmd, out_dir, env=env, do_overwrite=cfg.do_overwrite)
            except Exception as e:  # pragma: no cover
                raise ValueError(f"Failed to run {cfg.model} command {cmd}") from e

    logger.info(f"Model {cfg.model} finished successfully.")
