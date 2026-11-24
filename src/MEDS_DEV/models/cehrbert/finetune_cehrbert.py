import logging
import subprocess
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf

logger = logging.getLogger(__name__)

CONFIG = Path(__file__).parent / "_config.yaml"
finetune_yaml_template = Path(__file__).parent / "cehrbert_finetune_template.yaml"


# Duplicated this function from pretrain_cehrbert
# because import could not work from the model virtual environment
def run_subprocess(cmd: str, temp_work_dir: str, out_dir: Path) -> None:
    done_file = out_dir / ".done"
    if done_file.exists():
        logger.info(f"Skipping {cmd} because {done_file} exists.")
        return

    logger.info(f"Running model command: {cmd}")
    command_out = subprocess.run(cmd, shell=True, cwd=temp_work_dir, capture_output=True)
    command_errored = command_out.returncode != 0
    if command_errored:
        raise RuntimeError(
            f"{cmd} failed with exit code "
            f"{command_out.returncode}:\n"
            f"STDERR:\n{command_out.stderr.decode()}\n"
            f"STDOUT:\n{command_out.stdout.decode()}"
        )
    elif not out_dir.is_dir():
        raise RuntimeError(
            f"{cmd} failed to create output directory {out_dir}.\n"
            f"STDERR:\n{command_out.stderr.decode()}\n"
            f"STDOUT:\n{command_out.stdout.decode()}"
        )
    else:
        done_file.touch()


@hydra.main(version_base=None, config_path=str(CONFIG.parent.resolve()), config_name=CONFIG.stem)
def main(cfg: DictConfig) -> None:
    # Get the output dir
    output_dir = Path(cfg.output_dir)
    model_pretrained_dir = Path(cfg.model_initialization_dir)
    # Infer the task label
    task_label_name = Path(cfg.labels_dir).name
    # meds_reader dir
    meds_reader_dir = model_pretrained_dir / "meds_reader"
    # Pretrained model dir
    pretrained_model_dir = model_pretrained_dir / "pretrained_cehrbert"
    # Fine-tuned model dir
    finetuned_output_dir = output_dir / task_label_name
    finetuned_output_dir.mkdir(exist_ok=True, parents=True)

    # dataset_prepared_path
    dataset_prepared_path = output_dir / "dataset_prepared_path"
    logger.info(f"Creating the dataset_prepared output at {dataset_prepared_path}")

    # Open the YAML file
    finetune_yaml_file = output_dir / f"cehrbert_finetune_{task_label_name}.yaml"
    finetune_yaml = OmegaConf.load(str(finetune_yaml_template))
    finetune_yaml["model_name_or_path"] = str(pretrained_model_dir.resolve())
    finetune_yaml["tokenizer_name_or_path"] = str(pretrained_model_dir.resolve())
    finetune_yaml["output_dir"] = str(finetuned_output_dir.resolve())
    finetune_yaml["data_folder"] = str(meds_reader_dir.resolve())
    finetune_yaml["cohort_folder"] = cfg.labels_dir
    finetune_yaml["dataset_prepared_path"] = str(dataset_prepared_path.resolve())
    finetune_yaml["dataloader_num_workers"] = cfg.num_threads
    finetune_yaml["seed"] = cfg.seed
    finetune_yaml["do_train"] = True
    finetune_yaml["do_predict"] = True
    if cfg.get("demo", False):
        finetune_yaml["evaluation_strategy"] = "steps"
        finetune_yaml["save_strategy"] = "steps"
        finetune_yaml["max_steps"] = 10
        finetune_yaml["eval_steps"] = 10
        finetune_yaml["per_device_train_batch_size"] = 1
        finetune_yaml["preprocessing_num_workers"] = 1

    with open(finetune_yaml_file, "w") as file:
        file.write(OmegaConf.to_yaml(finetune_yaml))

    # run_finetune_runner.py is `python -m cehrbert.runners.hf_cehrbert_finetune_runner` with a workaround for
    # a cehrbert 1.5 regression (see that file).
    run_subprocess(
        cmd=f"python -u {Path(__file__).parent / 'run_finetune_runner.py'} {finetune_yaml_file}",
        temp_work_dir=str(output_dir),
        out_dir=finetuned_output_dir,
    )


if __name__ == "__main__":
    main()
