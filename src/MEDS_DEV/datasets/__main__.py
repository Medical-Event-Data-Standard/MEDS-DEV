import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig

from ..utils import clear_output_dir, run_in_env, temp_env
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


def format_build_command(
    command: str, output_dir: str, temp_dir: Path, raw_input_dir: str | Path | None = None
) -> str:
    """Fill in the path placeholders of a dataset build command.

    Args:
        command: The build command template, using `{output_dir}`, `{temp_dir}`, and `{raw_input_dir}`.
        output_dir: Where the final MEDS cohort is written.
        temp_dir: The directory for intermediate build files.
        raw_input_dir: A directory holding (or to receive) the raw source data. If `None`, `{temp_dir}/raw`
            is used, so the download does not outlive the build.

    Returns:
        The formatted build command, with absolute `temp_dir` and `raw_input_dir` paths.

    Examples:
        >>> cmd = "etl raw={raw_input_dir} tmp={temp_dir} out={output_dir}"
        >>> out = format_build_command(cmd, "meds", Path("build"))
        >>> out == f"etl raw={Path('build').resolve() / 'raw'} tmp={Path('build').resolve()} out=meds"
        True
        >>> out = format_build_command(cmd, "meds", Path("build"), raw_input_dir="downloads")
        >>> out == f"etl raw={Path('downloads').resolve()} tmp={Path('build').resolve()} out=meds"
        True
    """
    temp_dir = temp_dir.resolve()
    raw_input_dir = temp_dir / "raw" if raw_input_dir is None else Path(raw_input_dir).expanduser().resolve()
    return command.format(output_dir=output_dir, temp_dir=str(temp_dir), raw_input_dir=str(raw_input_dir))


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
        logger.info(f"Clearing existing output directory: {output_dir}")
        clear_output_dir(output_dir)

    done_fp = output_dir / ".done"
    if done_fp.is_file():  # pragma: no cover
        logger.info(f"Output directory {output_dir} already exists and is marked as done.")
        return

    build_cmd = _select_build_command(cfg.dataset, commands, cfg.demo)

    with temp_env(cfg, requirements) as (build_temp_dir, env):
        build_cmd = format_build_command(
            build_cmd, cfg.output_dir, build_temp_dir, raw_input_dir=cfg.get("raw_input_dir")
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
