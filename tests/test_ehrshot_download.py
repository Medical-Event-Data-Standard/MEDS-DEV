import io
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from MEDS_DEV.datasets.EHRShot import download


def make_meds_archive(path: Path, *, wrapped: bool = True, include_splits: bool = False) -> Path:
    meds_root = path.parent / f"{path.stem}-contents"
    data_dir = meds_root / "data"
    metadata_dir = meds_root / "metadata"
    data_dir.mkdir(parents=True)
    metadata_dir.mkdir()

    pl.DataFrame(
        {
            "subject_id": list(range(1, 11)),
            "time": [datetime(2020, 1, 1, tzinfo=UTC)] * 10,
            "code": ["SYNTHETIC/EVENT"] * 10,
        }
    ).write_parquet(data_dir / "part-0.parquet")
    (metadata_dir / "dataset.json").write_text('{"dataset_name": "synthetic"}\n')
    if include_splits:
        pl.DataFrame(
            {
                "subject_id": list(range(1, 11)),
                "split": ["train"] * 8 + ["tuning", "held_out"],
            }
        ).write_parquet(metadata_dir / "subject_splits.parquet")

    arcname = "meds_omop_ehrshot" if wrapped else "."
    with tarfile.open(path, mode="w:gz") as archive:
        archive.add(meds_root, arcname=arcname)
    return path


def fake_shard_subjects(subject_ids, **kwargs):
    assert set(subject_ids) == set(range(1, 11))
    assert kwargs == {
        "n_subjects_per_shard": 1000,
        "split_fracs_dict": {"train": 0.8, "tuning": 0.1, "held_out": 0.1},
        "seed": 1,
    }
    return {
        "train/0": list(range(1, 9)),
        "tuning/0": [9],
        "held_out/0": [10],
    }


def fake_pipeline_runner(command, *, check, env):
    assert command == ["MEDS_transform-pipeline", str(download.RESHARD_PIPELINE.resolve())]
    assert check is True

    input_dir = Path(env["EHRSHOT_INPUT_DIR"])
    output_dir = Path(env["EHRSHOT_OUTPUT_DIR"])
    events = pl.read_parquet(input_dir / "data" / "*.parquet")
    splits = pl.read_parquet(input_dir / "metadata" / "subject_splits.parquet")
    for split in ("train", "tuning", "held_out"):
        split_subjects = splits.filter(pl.col("split") == split).get_column("subject_id")
        split_dir = output_dir / "data" / split
        split_dir.mkdir(parents=True)
        events.filter(pl.col("subject_id").is_in(split_subjects)).write_parquet(split_dir / "0.parquet")

    return subprocess.CompletedProcess(command, 0)


class FakeRedivisFile:
    def __init__(self, source: Path):
        self.source = source
        self.calls = []

    def download(self, path: str, *, overwrite: bool, progress: bool) -> str:
        self.calls.append((path, overwrite, progress))
        shutil.copyfile(self.source, path)
        return path


@pytest.mark.parametrize("wrapped", [True, False])
def test_build_dataset_downloads_splits_and_reshards_synthetic_archive(tmp_path, wrapped):
    source = make_meds_archive(tmp_path / "source.tar.gz", wrapped=wrapped)
    remote_file = FakeRedivisFile(source)
    table = SimpleNamespace(file=lambda name: remote_file)
    redivis = SimpleNamespace(table=lambda reference: table)

    output_dir = tmp_path / "output"
    result = download.build_dataset(
        output_dir,
        tmp_path / "temp",
        redivis_module=redivis,
        shard_subjects_fn=fake_shard_subjects,
        pipeline_runner=fake_pipeline_runner,
    )

    assert result == output_dir.resolve()
    assert not (output_dir / "data" / "part-0.parquet").exists()
    assert {path.parent.name for path in (output_dir / "data").glob("*/*.parquet")} == {
        "train",
        "tuning",
        "held_out",
    }
    split_counts = (
        pl.read_parquet(output_dir / "metadata" / "subject_splits.parquet")
        .group_by("split")
        .len()
        .sort("split")
    )
    assert dict(zip(split_counts["split"], split_counts["len"], strict=True)) == {
        "held_out": 1,
        "train": 8,
        "tuning": 1,
    }
    assert (output_dir / "metadata" / "dataset.json").is_file()
    assert remote_file.calls == [(str((tmp_path / "temp" / download.ARCHIVE_NAME).resolve()), False, True)]


def test_create_subject_splits_preserves_existing_file(tmp_path):
    source = make_meds_archive(tmp_path / "source.tar.gz", include_splits=True)
    meds_root = download.extract_archive(source, tmp_path / "meds", tmp_path / "staging")
    splits_path = meds_root / "metadata" / "subject_splits.parquet"
    original = splits_path.read_bytes()

    result = download.create_subject_splits(
        meds_root,
        shard_subjects_fn=lambda *_args, **_kwargs: pytest.fail("should not replace existing splits"),
    )

    assert result == splits_path
    assert splits_path.read_bytes() == original


def test_create_subject_splits_requires_data_shards(tmp_path):
    meds_root = tmp_path / "meds"
    (meds_root / "data").mkdir(parents=True)
    (meds_root / "metadata").mkdir()

    with pytest.raises(ValueError, match="No MEDS data shards"):
        download.create_subject_splits(meds_root, shard_subjects_fn=fake_shard_subjects)


def test_create_subject_splits_rejects_invalid_assignment(tmp_path):
    source = make_meds_archive(tmp_path / "source.tar.gz")
    meds_root = download.extract_archive(source, tmp_path / "meds", tmp_path / "staging")

    with pytest.raises(ValueError, match="every subject exactly once"):
        download.create_subject_splits(
            meds_root,
            shard_subjects_fn=lambda *_args, **_kwargs: {"train/0": list(range(2, 12))},
        )


def test_reshard_to_splits_refuses_to_replace_metadata(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    (input_dir / "metadata").mkdir(parents=True)
    (output_dir / "metadata").mkdir(parents=True)

    with pytest.raises(FileExistsError, match="Refusing to replace existing output path"):
        download.reshard_to_splits(input_dir, output_dir, runner=lambda *_args, **_kwargs: None)


def test_reshard_to_splits_uses_subprocess_runner_by_default(tmp_path, monkeypatch):
    source = make_meds_archive(tmp_path / "source.tar.gz", include_splits=True)
    input_dir = download.extract_archive(source, tmp_path / "meds", tmp_path / "staging")
    output_dir = tmp_path / "output"
    monkeypatch.setattr(download.subprocess, "run", fake_pipeline_runner)

    result = download.reshard_to_splits(input_dir, output_dir)

    assert result == output_dir.resolve()
    assert (output_dir / "data" / "held_out" / "0.parquet").is_file()
    assert (output_dir / "metadata" / "dataset.json").is_file()


def test_download_uses_pinned_redivis_resource_names(tmp_path):
    source = make_meds_archive(tmp_path / "source.tar.gz", wrapped=False)
    remote_file = FakeRedivisFile(source)
    requested = {}

    def table(reference):
        requested["table"] = reference

        def file(name):
            requested["file"] = name
            return remote_file

        return SimpleNamespace(file=file)

    download.download_archive(tmp_path / "download.tar.gz", redivis_module=SimpleNamespace(table=table))

    assert requested == {
        "table": "shahlab.ehrshot:53gc:v3_2.files:4avd",
        "file": "meds_omop_ehrshot.tar.gz",
    }


def test_extract_archive_rejects_parent_path(tmp_path):
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        info = tarfile.TarInfo("../outside")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))

    with pytest.raises(ValueError, match="Unsafe path"):
        download.extract_archive(archive_path, tmp_path / "output", tmp_path / "staging")

    assert not (tmp_path / "outside").exists()


@pytest.mark.parametrize("link_type", [tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_extract_archive_rejects_links(tmp_path, link_type):
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        info = tarfile.TarInfo("link")
        info.type = link_type
        info.linkname = "target"
        archive.addfile(info)

    with pytest.raises(ValueError, match="Links are not allowed"):
        download.extract_archive(archive_path, tmp_path / "output", tmp_path / "staging")


def test_extract_archive_requires_meds_layout(tmp_path):
    archive_path = tmp_path / "not-meds.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        info = tarfile.TarInfo("README.txt")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"nope"))

    with pytest.raises(ValueError, match="does not contain a MEDS dataset root"):
        download.extract_archive(archive_path, tmp_path / "output", tmp_path / "staging")


def test_extract_archive_refuses_to_replace_existing_output(tmp_path):
    archive_path = make_meds_archive(tmp_path / "source.tar.gz")
    output_dir = tmp_path / "output"
    (output_dir / "data").mkdir(parents=True)

    with pytest.raises(FileExistsError, match="Refusing to replace existing output path"):
        download.extract_archive(archive_path, output_dir, tmp_path / "staging")


def test_download_module_cli(tmp_path, monkeypatch):
    source = make_meds_archive(tmp_path / "source.tar.gz")
    remote_file = FakeRedivisFile(source)
    table = SimpleNamespace(file=lambda name: remote_file)
    monkeypatch.setitem(sys.modules, "redivis", SimpleNamespace(table=lambda reference: table))
    monkeypatch.setattr(
        download,
        "create_subject_splits",
        lambda meds_root, **_kwargs: fake_create_splits(meds_root),
    )
    monkeypatch.setattr(
        download,
        "reshard_to_splits",
        lambda input_dir, output_dir, **_kwargs: fake_reshard(input_dir, output_dir),
    )

    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(download.__file__),
            "--output-dir",
            str(output_dir),
            "--temp-dir",
            str(temp_dir),
        ],
    )

    download.main()

    assert (output_dir / "data" / "train" / "0.parquet").is_file()
    assert (output_dir / "metadata" / "subject_splits.parquet").is_file()
    assert remote_file.calls == [(str((temp_dir / download.ARCHIVE_NAME).resolve()), False, True)]


def fake_create_splits(meds_root):
    splits_path = meds_root / "metadata" / "subject_splits.parquet"
    pl.DataFrame(
        {
            "subject_id": list(range(1, 11)),
            "split": ["train"] * 8 + ["tuning", "held_out"],
        }
    ).write_parquet(splits_path)
    return splits_path


def fake_reshard(input_dir, output_dir):
    fake_pipeline_runner(
        ["MEDS_transform-pipeline", str(download.RESHARD_PIPELINE.resolve())],
        check=True,
        env={"EHRSHOT_INPUT_DIR": str(input_dir), "EHRSHOT_OUTPUT_DIR": str(output_dir)},
    )
    shutil.copytree(input_dir / "metadata", output_dir / "metadata")
    return output_dir.resolve()
