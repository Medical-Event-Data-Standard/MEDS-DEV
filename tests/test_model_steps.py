"""Tests for `model.yaml` files (explicit, scoped steps), run through the real step runner."""

# ruff: noqa: E501

from pathlib import Path

import pytest
from omegaconf import OmegaConf

from MEDS_DEV import MODELS, TASKS
from MEDS_DEV.models import CFG_YAML, load_model_yaml
from MEDS_DEV.models.__main__ import main as meds_dev_model_main
from MEDS_DEV.models.__main__ import plan_from_cfg, task_inputs
from MEDS_DEV.models.steps import (
    PROFILE_STEPS,
    Overwrite,
    Scope,
    parse_step_graph,
    run_planned_steps,
    step_lock,
)
from MEDS_DEV.utils import run_in_env


def toy_graph(log_fp: Path):
    """A small `finetune` model whose steps append a word to `log_fp`, so tests can count executions."""
    return parse_step_graph(
        {
            "profile": "finetune",
            "steps": {
                "preprocess_data": f"echo preprocess >> {log_fp} && echo data > {{step_dir}}/data.txt",
                "pretrain": (
                    f"echo pretrain >> {log_fp} && cat {{preprocess_data_dir}}/data.txt > {{step_dir}}/weights.txt"
                ),
                "train_finetune": (
                    f"echo fit >> {log_fp} && test -f {{pretrain_dir}}/weights.txt "
                    "&& echo {labels_dir} > {step_dir}/head.txt"
                ),
                "predict_finetune": (
                    f"echo predict >> {log_fp} && cat {{pretrain_dir}}/weights.txt {{train_finetune_dir}}/head.txt "
                    "> {step_dir}/predictions_{split}.txt"
                ),
            },
        }
    )


def make_cfg(tmp_path: Path, **overrides):
    cfg = {
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
    head = tmp_path / "runs" / "DS" / "a" / "x" / "train_finetune" / "output" / "head.txt"
    assert Path(head.read_text().strip()).as_posix() == "/labels/a/x"


def test_shared_steps_are_reused_from_an_earlier_run(tmp_path: Path):
    """The flow of the integration fixtures: dataset steps in one run, the rest in another."""
    log_fp = tmp_path / "log.txt"
    graph = toy_graph(log_fp)

    pretrain_root = tmp_path / "pretrain_run"
    run(make_cfg(tmp_path, steps=["pretrain"], output_dir=str(pretrain_root)), graph)
    assert executions(log_fp) == ["preprocess", "pretrain"]

    run(
        make_cfg(
            tmp_path,
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
        steps=["predict_finetune"],
        task_name="t1",
        labels_dir="/labels/t1",
        split="tuning",
        step_dirs={"pretrain": str(existing)},
    )
    run(cfg, graph)

    # preprocess_data is only needed by pretrain, whose output is provided, so it does not run.
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


TEMPLATE_COMMANDS = {
    "preprocess_data": "m preprocess_data external_meds_dir={dataset_dir} external_predicates_file={predicates_path} output_data_dir={step_dir}",
    "pretrain": "m pretrain input_data_dir={preprocess_data_dir} output_pretrained_algorithm_dir={step_dir}",
    "train_supervised": "m train_supervised input_data_dir={preprocess_data_dir} external_labels_dir={labels_dir} output_supervised_algorithm_dir={step_dir}",
    "predict_supervised": "m predict_supervised input_data_dir={preprocess_data_dir} input_supervised_algorithm_dir={train_supervised_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}",
    "train_finetune": "m train_finetune input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_labels_dir={labels_dir} output_finetuned_algorithm_dir={step_dir}",
    "predict_finetune": "m predict_finetune input_data_dir={preprocess_data_dir} input_finetuned_algorithm_dir={train_finetune_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}",
    "infer_embeddings": "m infer_embeddings input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_index_dir={labels_dir} output_embeddings_dir={step_dir}",
    "train_probe": "m train_probe external_labels_dir={labels_dir} input_embeddings_dir={infer_embeddings_dir} output_probe_algorithm_dir={step_dir}",
    "predict_probe": "m predict_probe input_embeddings_dir={infer_embeddings_dir} input_probe_algorithm_dir={train_probe_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}",
    "predict_zero_shot_direct": "m predict_zero_shot_direct input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_index_dir={labels_dir} external_task_criteria_file={task_criteria_path} splits=[{split}] output_predictions_dir={step_dir}",
    "infer_trajectories": "m infer_trajectories input_data_dir={preprocess_data_dir} input_pretrained_algorithm_dir={pretrain_dir} external_index_dir={labels_dir} output_trajectories_dir={step_dir}",
    "predict_zero_shot_materialized": "m predict_zero_shot_materialized input_data_dir={preprocess_data_dir} input_trajectories_dir={infer_trajectories_dir} external_index_dir={labels_dir} external_task_criteria_file={task_criteria_path} splits=[{split}] output_predictions_dir={step_dir}",
    "predict_only": "m predict_only input_data_dir={preprocess_data_dir} external_index_dir={labels_dir} splits=[{split}] output_predictions_dir={step_dir}",
}


@pytest.mark.parametrize("profile", sorted(PROFILE_STEPS))
def test_every_profile_parses_with_its_template_commands(profile: str):
    """Each profile of the MEDS algorithm template is a valid model, with scopes and needs derived."""
    lifecycle = PROFILE_STEPS[profile]
    graph = parse_step_graph(
        {"profile": profile, "steps": {name: TEMPLATE_COMMANDS[name] for name in lifecycle}}
    )

    assert [step.name for step in graph.steps] == list(lifecycle)
    assert graph.predict_step.name == lifecycle[-1]
    assert [step.predict for step in graph.steps] == [False] * (len(lifecycle) - 1) + [True]
    for step in graph.steps:
        expected = Scope.DATASET if step.name in ("preprocess_data", "pretrain") else Scope.TASK
        assert step.scope == expected, step.name
    assert graph.by_name[lifecycle[1]].needs == ("preprocess_data",)


def test_steps_follow_the_profile_order_whatever_the_file_order():
    graph = parse_step_graph(
        {
            "profile": "supervised",
            "steps": {"predict_supervised": "p {train_supervised_dir}", "train_supervised": "t"},
        }
    )
    assert [step.name for step in graph.steps] == ["train_supervised", "predict_supervised"]
    assert graph.predict_step.needs == ("train_supervised",)


def test_registered_models_plan_for_two_tasks(tmp_path: Path):
    """Every registered model plans: shared steps once, task steps per task, predictions under `predict/`."""
    tasks = list(TASKS)[:2]  # registered tasks, so that zero-shot models get their criteria files
    for name, model in MODELS.items():
        graph = model["step_graph"]
        cfg = make_cfg(tmp_path, tasks=tasks, labels_root="/labels", predicates_path="/predicates.yaml")
        planned = plan_from_cfg(cfg, graph, model["model_dir"])

        n_shared = sum(step.scope == Scope.DATASET for step in graph.steps)
        n_task = len(graph.steps) - n_shared
        assert len(planned) == n_shared + 2 * n_task, name

        runs = tmp_path / "runs" / "DS"
        for p in planned:
            if p.task_name is None:
                assert p.run_dir == runs / "_shared" / p.step.name, name
            elif p.step.predict:
                assert p.run_dir == runs / p.task_name / "predict", name
            else:
                assert p.run_dir == runs / p.task_name / p.step.name, name
            assert "{" not in p.command, f"{name}: unformatted template variable in {p.command}"


def test_commands_block_is_rejected(tmp_path: Path):
    """The earlier format fails when the model is loaded, naming the model and how to migrate."""
    model_yaml = tmp_path / "model.yaml"
    model_yaml.write_text(
        "metadata: {description: d, contacts: [{name: n}]}\n"
        "commands: {supervised: {predict: 'p {output_dir}'}}\n"
    )
    with pytest.raises(ValueError, match=r"model old .*`commands` block is no longer supported"):
        load_model_yaml(model_yaml, "old")


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"steps": {"predict_only": "p"}}, "needs a `profile`"),
        ({"profile": "predict_only", "steps": ["predict_only"]}, "non-empty `steps` mapping"),
        (
            {"profile": "predict_only", "steps": {"predict_only": {"command": "p"}}},
            "non-empty command string",
        ),
        ({"profile": "predict_only", "steps": {"predict": "p"}}, "not part of profile 'predict_only'"),
        ({"profile": "probe", "steps": {"pretrain": "p", "predict_probe": "p"}}, "also needs step"),
    ],
)
def test_invalid_model_yaml(spec, message):
    with pytest.raises(ValueError, match=message):
        parse_step_graph(spec)


def test_selection_and_planning_errors(tmp_path: Path):
    graph = toy_graph(tmp_path / "log.txt")
    with pytest.raises(ValueError, match="Unknown step"):
        graph.closure(["nope"])
    with pytest.raises(ValueError, match="when running several tasks"):
        plan_from_cfg(
            make_cfg(tmp_path, tasks=["a", "b"], labels_root="/labels", step_dirs={"train_finetune": "/x"}),
            graph,
            Path("model_dir"),
        )


def test_step_lock_waits_then_times_out(tmp_path: Path):
    lock_fp = tmp_path / "step.lock"
    lock_fp.write_text("host=other pid=1\n")
    with (
        pytest.raises(TimeoutError, match="host=other pid=1"),
        step_lock(lock_fp, timeout=0.05, poll_interval=0.01),
    ):
        pass
    assert lock_fp.exists(), "a lock held by another run must not be removed"


def test_failing_step_is_reported(tmp_path: Path):
    graph = parse_step_graph({"profile": "predict_only", "steps": {"predict_only": "exit 3"}})
    cfg = make_cfg(tmp_path, task_name="t1")
    with pytest.raises(ValueError, match="Failed to run step predict_only: exit 3"):
        run(cfg, graph)


def test_meds_dev_model_main_runs_models(tmp_path: Path, monkeypatch):
    """`meds-dev-model`'s entry point plans and runs every step of a model (called without the CLI)."""
    log_fp = tmp_path / "log.txt"
    model = {
        "step_graph": toy_graph(log_fp),
        "model_dir": tmp_path / "model",
        "requirements": None,
    }
    monkeypatch.setitem(MODELS, "_test/toy", model)

    cfg = OmegaConf.merge(
        OmegaConf.load(CFG_YAML),
        {
            "model": "_test/toy",
            "dataset_dir": str(tmp_path / "data"),
            "dataset_name": "DS",
            "output_dir": str(tmp_path / "runs"),
            "task_name": "t1",
            "labels_dir": "/labels/t1",
        },
    )
    cfg.pop("hydra")
    meds_dev_model_main(cfg)
    meds_dev_model_main(OmegaConf.merge(cfg, {"overwrite": "task"}))

    assert executions(log_fp) == ["preprocess", "pretrain", "fit", "predict", "fit", "predict"]


def test_model_yaml_python_version(tmp_path: Path):
    """The optional `python` key is the version of the model's environment; it must be a string."""
    model_yaml = tmp_path / "model.yaml"
    body = (
        "metadata: {description: d, contacts: [{name: n}]}\nprofile: predict_only\nsteps: {predict_only: p}\n"
    )

    model_yaml.write_text(body)
    assert load_model_yaml(model_yaml, "m")["python"] is None
    model_yaml.write_text(body + 'python: "3.12"\n')
    assert load_model_yaml(model_yaml, "m")["python"] == "3.12"
    model_yaml.write_text(body + "python: 3.12\n")
    with pytest.raises(ValueError, match="`python` must be a version string"):
        load_model_yaml(model_yaml, "m")


def test_invalid_model_yaml_names_the_model(tmp_path: Path):
    model_yaml = tmp_path / "model.yaml"
    model_yaml.write_text("metadata: {description: d, contacts: [{name: n}]}\nprofile: probe\nsteps: {}\n")
    with pytest.raises(ValueError, match=r"Invalid model\.yaml for model broken"):
        load_model_yaml(model_yaml, "broken")
