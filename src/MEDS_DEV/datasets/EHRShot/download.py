"""Download and unpack the pre-built MEDS version of EHRShot from Redivis."""

import argparse
import logging
import shutil
import tarfile
from pathlib import Path, PurePosixPath
from types import ModuleType

logger = logging.getLogger(__name__)

TABLE_REFERENCE = "shahlab.ehrshot:53gc:v3_2.files:4avd"
ARCHIVE_NAME = "meds_omop_ehrshot.tar.gz"


def download_archive(destination: Path, *, redivis_module: ModuleType | None = None) -> Path:
    """Download the EHRShot MEDS archive to ``destination`` without reading it into memory."""
    if redivis_module is None:
        import redivis as redivis_module

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading %s from Redivis", ARCHIVE_NAME)
    table = redivis_module.table(TABLE_REFERENCE)
    remote_file = table.file(ARCHIVE_NAME)
    downloaded_path = Path(remote_file.download(str(destination), overwrite=False, progress=True))
    return downloaded_path.resolve()


def _validate_archive_members(archive: tarfile.TarFile) -> None:
    """Reject paths and links that could write outside the extraction directory."""
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe path in EHRShot archive: {member.name!r}")
        if member.issym() or member.islnk():
            raise ValueError(f"Links are not allowed in the EHRShot archive: {member.name!r}")


def _find_meds_root(extracted_dir: Path) -> Path:
    """Locate a MEDS root, allowing the archive to contain one wrapping directory."""

    def is_meds_root(path: Path) -> bool:
        return (path / "data").is_dir() and (path / "metadata").is_dir()

    if is_meds_root(extracted_dir):
        return extracted_dir

    children = list(extracted_dir.iterdir())
    if len(children) == 1 and children[0].is_dir() and is_meds_root(children[0]):
        return children[0]

    raise ValueError(
        "The downloaded archive does not contain a MEDS dataset root with data/ and metadata/ directories"
    )


def extract_archive(archive_path: Path, output_dir: Path, staging_dir: Path) -> Path:
    """Safely extract ``archive_path`` and place its MEDS root in ``output_dir``."""
    output_dir = output_dir.resolve()
    staging_dir = staging_dir.resolve()
    staging_dir.mkdir(parents=True, exist_ok=False)

    with tarfile.open(archive_path, mode="r:gz") as archive:
        _validate_archive_members(archive)
        archive.extractall(staging_dir, filter="fully_trusted")

    meds_root = _find_meds_root(staging_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in meds_root.iterdir():
        destination = output_dir / source.name
        if destination.exists():
            raise FileExistsError(f"Refusing to replace existing output path: {destination}")
        shutil.move(str(source), destination)

    return output_dir


def build_dataset(
    output_dir: Path,
    temp_dir: Path,
    *,
    redivis_module: ModuleType | None = None,
) -> Path:
    """Download the pre-built archive and unpack it into a MEDS dataset directory."""
    temp_dir = temp_dir.resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_archive(temp_dir / ARCHIVE_NAME, redivis_module=redivis_module)
    return extract_archive(archive_path, output_dir, temp_dir / "extracted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--temp-dir", required=True, type=Path)
    args = parser.parse_args()

    build_dataset(args.output_dir, args.temp_dir)


if __name__ == "__main__":
    main()
