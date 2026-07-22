import logging
import shutil
from pathlib import Path

import hydra
from omegaconf import DictConfig

from ..utils import run_in_env, temp_env
from . import CFG_YAML, DATASETS

logger = logging.getLogger(__name__)


def format_build_command(
    command: str, *, output_dir: str | Path, temp_dir: Path, raw_input_dir: str | Path | None = None
) -> str:
    """Format the paths exposed to dataset build commands.

    Args:
        command: Dataset build command template.
        output_dir: Destination for the MEDS dataset.
        temp_dir: Directory used for temporary build files.
        raw_input_dir: Existing raw dataset directory, or ``None`` to use a directory under ``temp_dir``.

    Returns:
        The formatted build command.

    Examples:
        >>> format_build_command(
        ...     "extract raw={raw_input_dir} tmp={temp_dir} out={output_dir}",
        ...     output_dir="meds",
        ...     temp_dir=Path("/tmp/build"),
        ... )
        'extract raw=/tmp/build/raw tmp=/tmp/build out=meds'
        >>> format_build_command(
        ...     "extract raw={raw_input_dir}",
        ...     output_dir="meds",
        ...     temp_dir=Path("/tmp/build"),
        ...     raw_input_dir="/datasets/mimiciv",
        ... )
        'extract raw=/datasets/mimiciv'
    """
    raw_input_dir = temp_dir / "raw" if raw_input_dir is None else Path(raw_input_dir).expanduser().resolve()
    return command.format(
        output_dir=output_dir,
        temp_dir=str(temp_dir.resolve()),
        raw_input_dir=str(raw_input_dir),
    )


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

    if cfg.demo:
        if "build_demo" not in commands:
            raise ValueError(
                f"Dataset {cfg.dataset} does not declare a build_demo command — `demo=True` is not "
                f"supported for this dataset. Build the full dataset instead (drop the `demo` arg)."
            )
        build_cmd = commands["build_demo"]
    else:
        build_cmd = commands["build_full"]

    with temp_env(cfg, requirements) as (build_temp_dir, env):
        build_cmd = format_build_command(
            build_cmd,
            output_dir=cfg.output_dir,
            temp_dir=build_temp_dir,
            raw_input_dir=cfg.get("raw_input_dir"),
        )

        logger.info(f"Considering running build command: {build_cmd}")
        run_in_env(
            build_cmd,
            cfg.output_dir,
            env=env,
            do_overwrite=cfg.do_overwrite,
            cwd=build_temp_dir,
        )
        logger.info(f"Build {cfg.dataset} command {build_cmd} completed successfully.")
