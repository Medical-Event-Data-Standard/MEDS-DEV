import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

import hydra
from omegaconf import DictConfig

from ..utils import run_in_env, temp_env
from . import CFG_YAML, DATASETS


@hydra.main(version_base=None, config_path=str(CFG_YAML.parent), config_name=CFG_YAML.stem)
def main(cfg: DictConfig):
    if cfg.dataset not in DATASETS:
        raise ValueError(
            f"Dataset {cfg.dataset} not currently configured! Available datasets: {DATASETS.keys()}"
        )

    commands = DATASETS[cfg.dataset]["commands"]
    requirements = DATASETS[cfg.dataset]["requirements"]

    output_dir = Path(cfg.output_dir)
    if cfg.get("do_overwrite", False) and output_dir.exists():  # pragma: no cover
        logger.info(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=False)

    done_fp = output_dir / ".done"
    if done_fp.is_file():  # pragma: no cover
        logger.info(f"Output directory {output_dir} already exists and is marked as done.")
        return

    build_cmd = commands["build_demo"] if cfg.demo else commands["build_full"]

    with temp_env(cfg, requirements) as (build_temp_dir, env):
        build_cmd = build_cmd.format(output_dir=cfg.output_dir, temp_dir=str(build_temp_dir.resolve()))

        logger.info(f"Considering running build command: {build_cmd}")
        run_in_env(build_cmd, cfg.output_dir, env=env, do_overwrite=cfg.do_overwrite, cwd=build_temp_dir)
        logger.info(f"Build {cfg.dataset} command {build_cmd} completed successfully.")
