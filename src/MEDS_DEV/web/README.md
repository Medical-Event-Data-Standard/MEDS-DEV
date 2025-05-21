# MEDS-DEV Web content

> [!WARNING]
> Still in progress!

This folder contains simple scripts used to collate data about the MEDS-DEV benchmark into JSON form for
ingestion in the [MEDS-DEV Website](https://medical-event-data-standard.github.io/MEDS-DEV).

Scripts:

## `aggregate_results.py`

This script aggregates all individual result JSON files from a directory (in normal usage sourced from the
GitHub repository's `_results` branch) into a single JSON blob and stores it in an output folder. It only
ingests new result blobs.

```bash
$ aggregate_results.py --input_dir ... --output-path ...
```

> [!NOTE]
> Results are assumed to be stored in individual subdirectories where the name of the subdirectory is a unique
> identifier for the result blob. This aligns with the GitHub Issue -> Result blob convention that names
> directories via the issue number.

> [!NOTE]
> This script is used to automatically aggregate new results via
> [a GitHub Action](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/aggregate_benchmark_results.yaml)

## `collate_entities.py`

This scripts collates information about the supported datasets, models, and tasks into a unified JSON blob.
