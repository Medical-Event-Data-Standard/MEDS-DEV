"""Writes a copy of a MEDS dataset's `codes.parquet` that GenHPF's preprocessing can read.

MEDS 0.4 makes the `description` column optional and MEDS-Extract 0.7 ETLs (e.g., eICU-MEDS 0.1.0) omit it,
but `genhpf-preprocess-meds` (as of genhpf 1.0.12) indexes it unconditionally. A missing column is added as
all empty strings, which GenHPF treats as a missing description and so uses the code string itself.
"""

import sys
from pathlib import Path

import polars as pl


def prepare_codes_metadata(metadata_dir: Path, output_dir: Path) -> None:
    """Copies `metadata_dir/codes.parquet` to `output_dir`, adding an empty `description` if missing.

    Args:
        metadata_dir: The `metadata` directory of the input MEDS dataset.
        output_dir: The directory to write the GenHPF-compatible `codes.parquet` to.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     in_dir, out_dir = Path(d) / "in", Path(d) / "out"
        ...     in_dir.mkdir()
        ...     pl.DataFrame({"code": ["LAB//sodium"]}).write_parquet(in_dir / "codes.parquet")
        ...     prepare_codes_metadata(in_dir, out_dir)
        ...     pl.read_parquet(out_dir / "codes.parquet").to_dicts()
        [{'code': 'LAB//sodium', 'description': ''}]

        Existing descriptions are kept:

        >>> with tempfile.TemporaryDirectory() as d:
        ...     in_dir, out_dir = Path(d) / "in", Path(d) / "out"
        ...     in_dir.mkdir()
        ...     codes = pl.DataFrame({"code": ["LAB//50983"], "description": ["Sodium"]})
        ...     codes.write_parquet(in_dir / "codes.parquet")
        ...     prepare_codes_metadata(in_dir, out_dir)
        ...     pl.read_parquet(out_dir / "codes.parquet").to_dicts()
        [{'code': 'LAB//50983', 'description': 'Sodium'}]
    """
    codes = pl.read_parquet(metadata_dir / "codes.parquet")
    if "description" not in codes.columns:
        codes = codes.with_columns(pl.lit("", dtype=pl.String).alias("description"))

    output_dir.mkdir(parents=True, exist_ok=True)
    codes.write_parquet(output_dir / "codes.parquet")


if __name__ == "__main__":
    prepare_codes_metadata(Path(sys.argv[1]), Path(sys.argv[2]))
