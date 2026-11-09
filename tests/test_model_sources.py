"""Tests for models registered by reference (`source.yaml`), using a fake GitHub instead of the network."""

import hashlib
import io
import json
import urllib.error
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from MEDS_DEV.models import MODELS, get_model, sources
from MEDS_DEV.models.__main__ import plan_from_cfg
from MEDS_DEV.models.fetch import fetch_models
from MEDS_DEV.models.steps import Scope, run_planned_steps
from MEDS_DEV.utils import run_in_env
from MEDS_DEV.web.collate_entities import collate_entities

REF = "0123456789abcdef0123456789abcdef01234567"
REPO = "https://github.com/org/my-algo"

V2_MODEL_YAML = b"""schema_version: 2
metadata:
  description: A remote zero-shot model.
  contacts:
    - name: Remote Author
profile: zero_shot_direct
steps:
  pretrain:
    scope: dataset
    command: echo weights > {step_dir}/w.txt
  predict_zero_shot_direct:
    scope: task
    needs: [pretrain]
    predict: true
    command: cat {pretrain_dir}/w.txt > {step_dir}/pred_{split}.txt && echo {task_criteria_path} >> {step_dir}/pred_{split}.txt
"""  # noqa: E501


class FakeGitHub:
    """Serves raw.githubusercontent.com files of one repository at one commit, and counts downloads."""

    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        prefix = f"https://raw.githubusercontent.com/org/my-algo/{REF}/"
        path = url.removeprefix(prefix)
        if not url.startswith(prefix) or path not in self.files:
            raise FileNotFoundError(url)
        return self.files[path]


@pytest.fixture
def github() -> FakeGitHub:
    return FakeGitHub(
        {
            "algorithms/zero_shot_direct/model.yaml": V2_MODEL_YAML,
            "pyproject.toml": b'[project]\nname = "my-algo"\n',
            "requirements.txt": b"-e .\nnumpy>=1.26\n",
        }
    )


def write_source(model_dir: Path, **overrides) -> Path:
    spec = {
        "repo": REPO,
        "ref": REF,
        "profile": "zero_shot_direct",
        "sha256": hashlib.sha256(V2_MODEL_YAML).hexdigest(),
    }
    spec.update(overrides)
    spec = {k: v for k, v in spec.items() if v is not None}
    model_dir.mkdir(parents=True, exist_ok=True)
    OmegaConf.save(OmegaConf.create({"source": spec}), model_dir / "source.yaml")
    return model_dir / "source.yaml"


@pytest.fixture
def remote_model(tmp_path: Path, monkeypatch, github: FakeGitHub):
    """Registers `_test/remote` from a source.yaml, with the fake GitHub and a temporary cache."""
    model_dir = tmp_path / "models" / "_test" / "remote"
    source = sources.read_source_file(write_source(model_dir))
    monkeypatch.setitem(MODELS, "_test/remote", {"source": source, "model_dir": model_dir})
    monkeypatch.setattr(sources, "http_fetch", github)
    monkeypatch.setenv(sources.CACHE_ENV_VAR, str(tmp_path / "cache"))
    return "_test/remote"


def test_get_model_fetches_validates_and_caches(remote_model: str, github: FakeGitHub, tmp_path: Path):
    entry = get_model(remote_model)

    assert entry["metadata"].description == "A remote zero-shot model."
    assert entry["schema_version"] == 2
    assert [step.scope for step in entry["step_graph"].steps] == [Scope.DATASET, Scope.TASK]
    assert entry["requirements"].read_text().splitlines() == [f"my-algo @ git+{REPO}@{REF}", "numpy>=1.26"]
    assert entry["requirements"].is_relative_to(tmp_path / "cache" / "org" / "my-algo" / REF)

    provenance = json.loads((entry["requirements"].parent / "source.json").read_text())
    assert provenance["ref"] == REF and provenance["path"] == "algorithms/zero_shot_direct/model.yaml"

    downloads = len(github.calls)
    del MODELS[remote_model]["step_graph"]  # simulate a new process: the registry entry is unresolved again
    get_model(remote_model)
    assert len(github.calls) == downloads, "a cached source must not be downloaded again"


def test_source_model_runs_end_to_end(remote_model: str, tmp_path: Path):
    entry = get_model(remote_model)
    cfg = OmegaConf.create(
        {
            "dataset_type": "full",
            "mode": "full",
            "dataset_dir": str(tmp_path / "data"),
            "dataset_name": "DS",
            "output_dir": str(tmp_path / "runs"),
            "task_name": "my_task",
            "labels_dir": str(tmp_path / "labels"),
            "task_criteria_path": "/criteria/my_task.yaml",
            "split": None,
            "demo": False,
        }
    )
    run_planned_steps(plan_from_cfg(cfg, entry["step_graph"], entry["model_dir"]), run_in_env)

    prediction = tmp_path / "runs" / "DS" / "my_task" / "predict" / "output" / "pred_held_out.txt"
    assert prediction.read_text().split() == ["weights", "/criteria/my_task.yaml"]


def test_changed_or_unpinned_model_yaml_is_rejected(tmp_path: Path, github: FakeGitHub):
    expected = hashlib.sha256(V2_MODEL_YAML).hexdigest()

    changed = sources.read_source_file(write_source(tmp_path / "a", sha256="f" * 64))
    with pytest.raises(ValueError, match=f"set source.sha256 to {expected}"):
        sources.resolve_source(changed, tmp_path / "cache", github)

    unpinned = sources.read_source_file(write_source(tmp_path / "b", sha256=None))
    with pytest.raises(ValueError, match=f"source.sha256 is not set.*{expected}"):
        sources.resolve_source(unpinned, tmp_path / "cache", github)

    assert not list((tmp_path / "cache").rglob("model.yaml")), "a rejected model.yaml must not be cached"


def test_missing_model_yaml(tmp_path: Path, github: FakeGitHub):
    source = sources.read_source_file(write_source(tmp_path / "a", profile="probe"))
    with pytest.raises(FileNotFoundError, match=r"algorithms/probe/model\.yaml"):
        sources.resolve_source(source, tmp_path / "cache", github)


def test_read_source_file_rejects_extra_keys(tmp_path: Path):
    fp = write_source(tmp_path / "a")
    OmegaConf.save(OmegaConf.merge(OmegaConf.load(fp), {"metadata": {"description": "x"}}), fp)
    with pytest.raises(ValueError, match="exactly one top-level key"):
        sources.read_source_file(fp)


def test_fetch_models_cli(remote_model: str, monkeypatch, capsys):
    assert fetch_models() == [(remote_model, None)]

    from MEDS_DEV.models import fetch

    fetch.main([remote_model])
    assert f"{remote_model}: ok" in capsys.readouterr().out

    with pytest.raises(ValueError, match=r"Not models registered through source\.yaml"):
        fetch_models(["random_predictor"])


def test_fetch_models_cli_reports_failures(tmp_path: Path, monkeypatch, github: FakeGitHub, capsys):
    model_dir = tmp_path / "models" / "_test" / "unpinned"
    source = sources.read_source_file(write_source(model_dir, sha256=None))
    monkeypatch.setitem(MODELS, "_test/unpinned", {"source": source, "model_dir": model_dir})
    monkeypatch.setattr(sources, "http_fetch", github)
    monkeypatch.setenv(sources.CACHE_ENV_VAR, str(tmp_path / "cache"))

    from MEDS_DEV.models import fetch

    with pytest.raises(SystemExit) as exc:
        fetch.main(["_test/unpinned"])
    assert exc.value.code == 1
    assert "set source.sha256 to" in capsys.readouterr().out


def test_collate_entities_includes_source_models(tmp_path: Path, monkeypatch, github: FakeGitHub):
    monkeypatch.setattr(sources, "http_fetch", github)
    monkeypatch.setenv(sources.CACHE_ENV_VAR, str(tmp_path / "cache"))

    repo = tmp_path / "repo" / "src" / "MEDS_DEV"
    (repo / "datasets").mkdir(parents=True)
    (repo / "tasks").mkdir()
    (repo / "models" / "local").mkdir(parents=True)
    (repo / "models" / "local" / "model.yaml").write_text("metadata: {description: local}\n")
    write_source(repo / "models" / "remote")
    (repo / "models" / "remote" / "README.md").write_text("# Remote\n")

    collate_entities(tmp_path / "repo", tmp_path / "out", do_overwrite=True)
    models = json.loads((tmp_path / "out" / "models.json").read_text())

    remote = models["remote"]["data"]
    assert remote["entity"]["metadata"]["description"] == "A remote zero-shot model."
    assert remote["source"] == {
        "repo": REPO,
        "ref": REF,
        "path": "algorithms/zero_shot_direct/model.yaml",
        "sha256": hashlib.sha256(V2_MODEL_YAML).hexdigest(),
    }
    assert remote["requirements"][0] == f"my-algo @ git+{REPO}@{REF}"
    assert remote["readme"] == "# Remote\n"
    assert models["local"]["data"]["entity"]["metadata"]["description"] == "local"


def test_http_fetch(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["auth"] = request.get_header("Authorization")
        if request.full_url.endswith("missing"):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, io.BytesIO())
        return io.BytesIO(b"content")

    monkeypatch.setattr(sources.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv(sources.TOKEN_ENV_VAR, "secret")

    assert sources.http_fetch("https://raw.githubusercontent.com/org/m/sha/file") == b"content"
    assert seen["auth"] == "Bearer secret"

    sources.http_fetch("https://example.com/file")
    assert seen["auth"] is None, "the token must only be sent to GitHub"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        sources.http_fetch("https://raw.githubusercontent.com/org/m/sha/missing")
