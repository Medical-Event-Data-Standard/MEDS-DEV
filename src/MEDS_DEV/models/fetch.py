"""`meds-dev-fetch-models`: fetch and verify the models registered through a `source.yaml`.

Use it to fill the cache before running on a machine without network access, or to get the `sha256` to pin
in a new `source.yaml` (a source without one fails with the hash of the pinned `model.yaml`).
"""

import argparse
import sys
from pathlib import Path

from . import MODELS, get_model
from .sources import default_cache_dir


def fetch_models(
    names: list[str] | None = None, cache_dir: Path | None = None
) -> list[tuple[str, str | None]]:
    """Fetches the named source models (default: all of them); returns `(name, error or None)` pairs."""
    source_models = [name for name, entry in MODELS.items() if "source" in entry]
    if names:
        unknown = [name for name in names if name not in source_models]
        if unknown:
            raise ValueError(
                f"Not models registered through source.yaml: {unknown}. Source models: {source_models}"
            )
        source_models = names

    results = []
    for name in source_models:
        try:
            get_model(name, cache_dir=cache_dir)
        except (ValueError, FileNotFoundError, OSError) as e:
            results.append((name, str(e)))
        else:
            results.append((name, None))
    return results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", help="Models to fetch (default: every source.yaml model).")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=f"Cache directory (default: $MEDS_DEV_SOURCE_CACHE or {default_cache_dir()}).",
    )
    args = parser.parse_args(argv)

    results = fetch_models(args.models or None, args.cache_dir)
    if not results:
        print("No models are registered through source.yaml.")
    for name, error in results:
        print(f"{name}: {'ok' if error is None else 'FAILED: ' + error}")
    if any(error is not None for _, error in results):
        sys.exit(1)
