import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig

from .. import DATASETS
from ..utils import run_in_env
from . import CFG_YAML, TASKS

logger = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path=str(CFG_YAML.parent), config_name=CFG_YAML.stem)
def main(cfg: DictConfig):
    if cfg.task not in TASKS:
        raise ValueError(f"Task {cfg.task} not currently configured. Configured tasks: {TASKS.keys()}")

    task_config_path = TASKS[cfg.task]["criteria_fp"]
    if cfg.get("dataset_predicates_path", None):
        logger.info(f"Using provided (local) predicates path: {cfg.dataset_predicates_path}")
        dataset_predicates_path = Path(cfg.dataset_predicates_path)
    else:
        if cfg.dataset not in DATASETS:
            raise ValueError(
                f"Dataset {cfg.dataset} not currently configured! Available datasets: {DATASETS.keys()}"
            )
        dataset_predicates_path = DATASETS[cfg.dataset]["predicates"]

    logger.info(f"Running task {cfg.task} on dataset {cfg.dataset}")

    cmd = " ".join(
        [
            "aces-cli",
            "--multirun",
            f"cohort_name={cfg.task}",
            "data=sharded",
            "data.standard=meds",
            f"data.root={cfg.dataset_dir}/data",
            f"data.shard=$(expand_shards {cfg.dataset_dir}/data)",
            f"config_path={task_config_path}",
            f"predicates_path={dataset_predicates_path}",
            f"output_filepath={cfg.output_dir}" + r"/\$\{data._prefix\}.parquet",
            f"log_dir={cfg.output_dir}/.logs",
        ]
    )

    logger.info(f"Running ACES: {cmd}")
    run_in_env(
        cmd=cmd,
        output_dir=cfg.output_dir,
        do_overwrite=cfg.do_overwrite,
        run_as_script=False,
    )
    logger.info(f"Extract {cfg.task} for {cfg.dataset} command {cmd} finished successfully.")
