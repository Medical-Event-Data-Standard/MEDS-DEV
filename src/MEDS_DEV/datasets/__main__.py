import logging
import shutil
from pathlib import Path

import hydra
from omegaconf import DictConfig

from ..utils import run_in_env, temp_env
from . import CFG_YAML, DATASETS

logger = logging.getLogger(__name__)


def _select_build_command(dataset: str, commands: dict, demo: bool) -> str:
    """Return the build command for the requested build mode.

    ``build_full`` is always required; ``build_demo`` is optional (a dataset may have no demo
    recipe). Requesting ``demo=True`` for a dataset that does not declare ``build_demo`` is an error.

    Args:
        dataset: The dataset name, used only for the error message.
        commands: The dataset's ``commands`` mapping (must contain ``build_full``; may contain
            ``build_demo``).
        demo: Whether the demo build was requested.

    Returns:
        The selected build command string.

    Raises:
        ValueError: If ``demo`` is ``True`` but ``commands`` has no ``build_demo`` entry.

    Examples:
        >>> cmds = {"build_full": "full-cmd", "build_demo": "demo-cmd"}
        >>> _select_build_command("D", cmds, demo=False)
        'full-cmd'
        >>> _select_build_command("D", cmds, demo=True)
        'demo-cmd'
        >>> _select_build_command("D", {"build_full": "full-cmd"}, demo=False)
        'full-cmd'
        >>> _select_build_command("D", {"build_full": "full-cmd"}, demo=True)
        Traceback (most recent call last):
            ...
        ValueError: Dataset D does not declare a build_demo command — `demo=True` is not supported
        for this dataset. Build the full dataset instead (drop the `demo` arg).
    """
    if demo:
        if "build_demo" not in commands:
            raise ValueError(
                f"Dataset {dataset} does not declare a build_demo command — `demo=True` is not "
                f"supported for this dataset. Build the full dataset instead (drop the `demo` arg)."
            )
        return commands["build_demo"]
    return commands["build_full"]


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

    build_cmd = _select_build_command(cfg.dataset, commands, cfg.demo)

    with temp_env(cfg, requirements) as (build_temp_dir, env):
        build_cmd = build_cmd.format(output_dir=cfg.output_dir, temp_dir=str(build_temp_dir.resolve()))

        logger.info(f"Considering running build command: {build_cmd}")
        run_in_env(
            build_cmd,
            cfg.output_dir,
            env=env,
            do_overwrite=cfg.do_overwrite,
            cwd=build_temp_dir,
        )
        logger.info(f"Build {cfg.dataset} command {build_cmd} completed successfully.")
