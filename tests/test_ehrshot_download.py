import io
import runpy
import shutil
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from MEDS_DEV.datasets.EHRShot import download


def make_meds_archive(path: Path, *, wrapped: bool = True) -> Path:
    prefix = "meds_omop_ehrshot/" if wrapped else ""
    with tarfile.open(path, mode="w:gz") as archive:
        for name, contents in {
            f"{prefix}data/part-0.parquet": b"synthetic-data",
            f"{prefix}metadata/subject_splits.parquet": b"synthetic-metadata",
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            archive.addfile(info, io.BytesIO(contents))
    return path


class FakeRedivisFile:
    def __init__(self, source: Path):
        self.source = source
        self.calls = []

    def download(self, path: str, *, overwrite: bool, progress: bool) -> str:
        self.calls.append((path, overwrite, progress))
        shutil.copyfile(self.source, path)
        return path


@pytest.mark.parametrize("wrapped", [True, False])
def test_build_dataset_downloads_expected_file_and_extracts_synthetic_archive(tmp_path, wrapped):
    source = make_meds_archive(tmp_path / "source.tar.gz", wrapped=wrapped)
    remote_file = FakeRedivisFile(source)
    table = SimpleNamespace(file=lambda name: remote_file)
    redivis = SimpleNamespace(table=lambda reference: table)

    output_dir = tmp_path / "output"
    result = download.build_dataset(output_dir, tmp_path / "temp", redivis_module=redivis)

    assert result == output_dir.resolve()
    assert (output_dir / "data" / "part-0.parquet").is_file()
    assert (output_dir / "metadata" / "subject_splits.parquet").is_file()
    assert remote_file.calls == [(str((tmp_path / "temp" / download.ARCHIVE_NAME).resolve()), False, True)]


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

    runpy.run_path(download.__file__, run_name="__main__")

    assert (output_dir / "data" / "part-0.parquet").is_file()
    assert (output_dir / "metadata" / "subject_splits.parquet").is_file()
    assert remote_file.calls == [(str((temp_dir / download.ARCHIVE_NAME).resolve()), False, True)]
