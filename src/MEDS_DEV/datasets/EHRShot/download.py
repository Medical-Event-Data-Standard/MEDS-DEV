"""Download and unpack the pre-built MEDS version of EHRShot from Redivis."""

import argparse
import logging
import os
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from types import ModuleType

logger = logging.getLogger(__name__)

TABLE_REFERENCE = "shahlab.ehrshot:53gc:v3_2.files:4avd"
ARCHIVE_NAME = "meds_omop_ehrshot.tar.gz"
RESHARD_PIPELINE = Path(__file__).with_name("reshard.yaml")
SPLIT_FRACTIONS = {"train": 0.8, "tuning": 0.1, "held_out": 0.1}
SPLIT_SEED = 1
N_SUBJECTS_PER_SHARD = 1000


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


def create_subject_splits(meds_root: Path, *, shard_subjects_fn=None) -> Path:
    """Create deterministic MIMIC-style subject splits for an extracted MEDS dataset."""
    import polars as pl

    splits_path = meds_root / "metadata" / "subject_splits.parquet"
    if splits_path.exists():
        logger.info("Preserving existing subject splits at %s", splits_path)
        return splits_path

    if shard_subjects_fn is None:
        from MEDS_transforms.stages.reshard_to_split.reshard_to_split import shard_subjects

        shard_subjects_fn = shard_subjects

    data_files = sorted((meds_root / "data").rglob("*.parquet"))
    if not data_files:
        raise ValueError(f"No MEDS data shards found under {meds_root / 'data'}")

    subject_ids = (
        pl.scan_parquet([str(path) for path in data_files])
        .select(pl.col("subject_id").cast(pl.Int64))
        .unique()
        .collect()["subject_id"]
        .to_numpy()
    )
    split_shards = shard_subjects_fn(
        subject_ids,
        n_subjects_per_shard=N_SUBJECTS_PER_SHARD,
        split_fracs_dict=SPLIT_FRACTIONS,
        seed=SPLIT_SEED,
    )

    split_subject_ids = []
    split_names = []
    for shard_name, shard_subject_ids in split_shards.items():
        split_name = shard_name.rsplit("/", 1)[0]
        split_subject_ids.extend(shard_subject_ids)
        split_names.extend([split_name] * len(shard_subject_ids))

    if set(split_subject_ids) != set(subject_ids) or len(split_subject_ids) != len(subject_ids):
        raise ValueError("Generated subject splits do not contain every subject exactly once")

    splits = pl.DataFrame(
        {"subject_id": split_subject_ids, "split": split_names},
        schema={"subject_id": pl.Int64, "split": pl.String},
    ).sort("subject_id")
    splits_path.parent.mkdir(parents=True, exist_ok=True)
    splits.write_parquet(splits_path)
    return splits_path


def reshard_to_splits(input_dir: Path, output_dir: Path, *, runner=None) -> Path:
    """Use MEDS-Transforms to rewrite flat input shards into split directories."""
    source_metadata = input_dir / "metadata"
    output_metadata = output_dir / "metadata"
    if output_metadata.exists():
        raise FileExistsError(f"Refusing to replace existing output path: {output_metadata}")

    if runner is None:
        runner = subprocess.run

    env = os.environ.copy()
    env["EHRSHOT_INPUT_DIR"] = str(input_dir.resolve())
    env["EHRSHOT_OUTPUT_DIR"] = str(output_dir.resolve())
    runner(["MEDS_transform-pipeline", str(RESHARD_PIPELINE.resolve())], check=True, env=env)

    shutil.copytree(source_metadata, output_metadata)
    return output_dir.resolve()


def build_dataset(
    output_dir: Path,
    temp_dir: Path,
    *,
    redivis_module: ModuleType | None = None,
    shard_subjects_fn=None,
    pipeline_runner=None,
) -> Path:
    """Download EHRShot, create deterministic splits, and produce split-aware MEDS shards."""
    temp_dir = temp_dir.resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_archive(temp_dir / ARCHIVE_NAME, redivis_module=redivis_module)
    raw_meds_dir = extract_archive(archive_path, temp_dir / "raw_meds", temp_dir / "extracted")
    create_subject_splits(raw_meds_dir, shard_subjects_fn=shard_subjects_fn)
    return reshard_to_splits(raw_meds_dir, output_dir, runner=pipeline_runner)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--temp-dir", required=True, type=Path)
    args = parser.parse_args()

    build_dataset(args.output_dir, args.temp_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
