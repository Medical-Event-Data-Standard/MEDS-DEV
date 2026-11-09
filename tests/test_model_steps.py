"""Tests for version 2 `model.yaml` files (explicit, scoped steps), run through the real step runner."""

# ruff: noqa: E501

from pathlib import Path

import pytest
import yaml
from omegaconf import OmegaConf

from MEDS_DEV import MODELS, TASKS
from MEDS_DEV.models import get_model
from MEDS_DEV.models.__main__ import plan_from_cfg, task_inputs
from MEDS_DEV.models.steps import (
    Overwrite,
    Profile,
    Scope,
    load_step_graph,
    parse_step_graph,
    run_planned_steps,
)
from MEDS_DEV.utils import run_in_env


def toy_graph(log_fp: Path):
    """A small v2 model whose steps append their name to `log_fp`, so tests can count executions."""
    return parse_step_graph(
        {
            "schema_version": 2,
            "steps": {
                "preprocess": {
                    "scope": "dataset",
                    "command": f"echo preprocess >> {log_fp} && echo data > {{step_dir}}/data.txt",
                },
                "pretrain": {
                    "scope": "dataset",
                    "needs": ["preprocess"],
                    "command": (
                        f"echo pretrain >> {log_fp} && cat {{preprocess_dir}}/data.txt > {{step_dir}}/weights.txt"
                    ),
                },
                "fit": {
                    "scope": "task",
                    "needs": ["pretrain"],
                    "command": f"echo fit >> {log_fp} && echo {{labels_dir}} > {{step_dir}}/head.txt",
                },
                "predict_task": {
                    "scope": "task",
                    "needs": ["pretrain", "fit"],
                    "predict": True,
                    "command": (
                        f"echo predict >> {log_fp} && cat {{pretrain_dir}}/weights.txt {{fit_dir}}/head.txt "
                        "> {step_dir}/predictions_{split}.txt"
                    ),
                },
            },
        }
    )


def make_cfg(tmp_path: Path, **overrides):
    cfg = {
        "dataset_type": "full",
        "mode": "full",
        "dataset_dir": str(tmp_path / "data"),
        "dataset_name": "DS",
        "output_dir": str(tmp_path / "runs"),
        "demo": False,
        "split": None,
        "task_name": None,
        "labels_dir": None,
        "model_initialization_dir": None,
        "predicates_path": None,
        "task_criteria_path": None,
        "steps": None,
        "tasks": None,
        "labels_root": None,
        "step_dirs": {},
    }
    cfg.update(overrides)
    return OmegaConf.create(cfg)


def run(cfg, graph, overwrite=Overwrite.NONE):
    run_planned_steps(plan_from_cfg(cfg, graph, Path("model_dir")), run_in_env, overwrite=overwrite)


def executions(log_fp: Path) -> list[str]:
    return log_fp.read_text().split() if log_fp.exists() else []


def test_shared_steps_run_once_across_tasks(tmp_path: Path):
    log_fp = tmp_path / "log.txt"
    graph = toy_graph(log_fp)

    run(make_cfg(tmp_path, task_name="t1", labels_dir="/labels/t1"), graph)
    run(make_cfg(tmp_path, task_name="t2", labels_dir="/labels/t2"), graph)

    assert executions(log_fp) == ["preprocess", "pretrain", "fit", "predict", "fit", "predict"]

    runs = tmp_path / "runs" / "DS"
    assert (runs / "_shared" / "pretrain" / "output" / "weights.txt").read_text().strip() == "data"
    assert (runs / "_shared" / "pretrain" / ".done").is_file()
    predictions = (runs / "t2" / "predict" / "output" / "predictions_held_out.txt").read_text().split()
    assert predictions == ["data", "/labels/t2"]


def test_tasks_list_runs_every_task_in_one_call(tmp_path: Path):
    log_fp = tmp_path / "log.txt"
    run(make_cfg(tmp_path, tasks=["a/x", "b"], labels_root="/labels"), toy_graph(log_fp))

    assert executions(log_fp) == ["preprocess", "pretrain", "fit", "predict", "fit", "predict"]
    head = tmp_path / "runs" / "DS" / "a" / "x" / "fit" / "output" / "head.txt"
    assert Path(head.read_text().strip()).as_posix() == "/labels/a/x"


def test_unsupervised_then_supervised_reuses_shared_steps(tmp_path: Path):
    """The flow of the integration fixtures: dataset steps in one run, task steps in another."""
    log_fp = tmp_path / "log.txt"
    graph = toy_graph(log_fp)

    pretrain_root = tmp_path / "pretrain_run"
    run(make_cfg(tmp_path, dataset_type="unsupervised", mode="train", output_dir=str(pretrain_root)), graph)
    assert executions(log_fp) == ["preprocess", "pretrain"]

    run(
        make_cfg(
            tmp_path,
            dataset_type="supervised",
            mode="full",
            task_name="t1",
            labels_dir="/labels/t1",
            model_initialization_dir=str(pretrain_root),
        ),
        graph,
    )
    assert executions(log_fp) == ["preprocess", "pretrain", "fit", "predict"]
    assert not (tmp_path / "runs" / "DS" / "_shared").exists()


def test_overwrite_task_keeps_shared_steps(tmp_path: Path):
    log_fp = tmp_path / "log.txt"
    graph = toy_graph(log_fp)
    cfg = make_cfg(tmp_path, task_name="t1", labels_dir="/labels/t1")

    run(cfg, graph)
    run(cfg, graph, overwrite=Overwrite.TASK)
    assert executions(log_fp) == ["preprocess", "pretrain", "fit", "predict", "fit", "predict"]

    run(cfg, graph, overwrite=Overwrite.ALL)
    assert executions(log_fp)[6:] == ["preprocess", "pretrain", "fit", "predict"]


def test_steps_and_step_dirs(tmp_path: Path):
    log_fp = tmp_path / "log.txt"
    graph = toy_graph(log_fp)

    existing = tmp_path / "existing_pretrain"
    existing.mkdir()
    (existing / "weights.txt").write_text("external\n")

    cfg = make_cfg(
        tmp_path,
        steps=["predict_task"],
        task_name="t1",
        labels_dir="/labels/t1",
        split="tuning",
        step_dirs={"pretrain": str(existing)},
    )
    run(cfg, graph)

    # preprocess is only needed by pretrain, whose output is provided, so it does not run.
    assert executions(log_fp) == ["fit", "predict"]
    out = tmp_path / "runs" / "DS" / "t1" / "predict.tuning" / "output" / "predictions_tuning.txt"
    assert out.read_text().split() == ["external", "/labels/t1"]


def test_task_inputs():
    assert task_inputs(OmegaConf.create({"task_name": None})) == []

    with pytest.raises(ValueError, match="labels_root must be set"):
        task_inputs(OmegaConf.create({"tasks": ["a"]}))
    with pytest.raises(ValueError, match="task_criteria_path cannot be combined with tasks"):
        task_inputs(OmegaConf.create({"tasks": ["a"], "labels_root": "/l", "task_criteria_path": "/c.yaml"}))

    task_name = next(iter(TASKS))
    (inputs,) = task_inputs(OmegaConf.create({"task_name": task_name, "labels_dir": "/l"}))
    assert inputs.task_criteria_path == str(TASKS[task_name]["criteria_fp"])

    (inputs,) = task_inputs(
        OmegaConf.create({"task_name": task_name, "labels_dir": "/l", "task_criteria_path": "/local.yaml"})
    )
    assert inputs.task_criteria_path == "/local.yaml"


def test_missing_task_fails_before_running(tmp_path: Path):
    log_fp = tmp_path / "log.txt"
    with pytest.raises(ValueError, match="task_name"):
        plan_from_cfg(make_cfg(tmp_path), toy_graph(log_fp), Path("model_dir"))
    assert not log_fp.exists()


TEMPLATE_LIKE_MODELS = {
    "probe": """
schema_version: 2
profile: probe
steps:
  preprocess_data:
    scope: dataset
    command: m preprocess_data external_meds_dir={dataset_dir} external_predicates_file={predicates_path} output_data_dir={step_dir}
  pretrain:
    scope: dataset
    needs: [preprocess_data]
    command: m pretrain input_data_dir={preprocess_data_dir} output_pretrained_algorithm_dir={step_dir}
  infer_embeddings:
    scope: task
    needs: [preprocess_data, pretrain]
    command: m infer_embeddings input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_index_dir={labels_dir} output_embeddings_dir={step_dir}
  train_probe:
    scope: task
    needs: [infer_embeddings]
    command: m train_probe external_labels_dir={labels_dir} input_embeddings_dir={infer_embeddings_dir} output_probe_algorithm_dir={step_dir}
  predict_probe:
    scope: task
    needs: [infer_embeddings, train_probe]
    predict: true
    command: m predict_probe input_embeddings_dir={infer_embeddings_dir} input_probe_algorithm_dir={train_probe_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}
""",
    "zero_shot_direct": """
schema_version: 2
profile: zero_shot_direct
steps:
  preprocess_data:
    scope: dataset
    command: m preprocess_data external_meds_dir={dataset_dir} output_data_dir={step_dir}
  pretrain:
    scope: dataset
    needs: [preprocess_data]
    command: m pretrain input_data_dir={preprocess_data_dir} output_pretrained_algorithm_dir={step_dir}
  predict_zero_shot_direct:
    scope: task
    needs: [preprocess_data, pretrain]
    predict: true
    command: m predict input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_index_dir={labels_dir} external_task_criteria_file={task_criteria_path} splits=[{split}] output_predictions_dir={step_dir}
""",
    "supervised": """
schema_version: 2
profile: supervised
steps:
  preprocess_data:
    scope: dataset
    command: m preprocess_data external_meds_dir={dataset_dir} output_data_dir={step_dir}
  train_supervised:
    scope: task
    needs: [preprocess_data]
    command: m train_supervised input_data_dir={preprocess_data_dir} external_labels_dir={labels_dir} output_supervised_algorithm_dir={step_dir}
  predict_supervised:
    scope: task
    needs: [preprocess_data, train_supervised]
    predict: true
    command: m predict_supervised input_data_dir={preprocess_data_dir} input_supervised_algorithm_dir={train_supervised_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}
""",
}


@pytest.mark.parametrize("profile", sorted(TEMPLATE_LIKE_MODELS))
def test_template_like_models_validate(profile: str):
    graph = load_step_graph(yaml.safe_load(TEMPLATE_LIKE_MODELS[profile]))
    assert graph.profile == Profile(profile)
    assert graph.steps[0].scope == Scope.DATASET


def test_registered_v1_models_are_described_by_step_graphs():
    for name in MODELS:
        model = get_model(name)
        if model["schema_version"] != 1:
            continue
        graph = model["step_graph"]
        commands = model["commands"]
        if (commands.get("supervised") or {}).get("predict"):
            assert graph.predict_step is not None and graph.predict_step.name == "supervised_predict", name
        if (commands.get("unsupervised") or {}).get("train"):
            assert graph.by_name["unsupervised_train"].scope == Scope.DATASET, name
