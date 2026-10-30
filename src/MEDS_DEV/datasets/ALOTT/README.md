# ALarms, Outcomes Telemetry with Timing (ALOTT)

## Description

ALOTT (ALarms, Outcomes Telemetry with Timing) is a pilot bedside-EMR database from two hospitals,
collected to support algorithms that predict emergency response team events. It pairs bedside
telemetry from 270 beds with electronic medical record data: admissions, diagnoses, ICU stays and bed
moves, labs, orders, medications and nursing flowsheets. MEDS-DEV uses the EMR tables only.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/alott/1.0.0/):

- **Access Policy**: Restricted access
- **License (for files)**: PhysioNet Restricted Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Restricted Health Data Use Agreement Version 1.5.0
- **Required training**: none

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.

## Supported Tasks

- The six blood `abnormal_lab/*/first_24h` tasks: definable, with caveats. Labs carry only a result
    *date* and are placed at 23:59:59, so the tasks' 24 h windows act as calendar days (input =
    admission day, target = next day). There is no birth date or age, so children cannot be excluded.
    Lab codes are `LAB//RESULT//<panel>//<component>`; units are US (the code carries none).
- `mortality/in_icu/first_24h`: not supported. The release has no death information; the task would
    run but every label would be False. ICU predicates are defined only because metabolic acidosis
    stops at ICU discharge.
- `abnormal_lab/vital/hypotension/first_24h`: not supported. The EMR flowsheet has no blood pressure.

These tasks are not yet listed in their `supported_datasets`; that follows in a separate PR once
all four local datasets (Zigong, PICdb, ALOTT, CDSL) are registered, to avoid conflicting edits.

## MEDS Transformation

[`ALOTT-MEDS`](https://github.com/rvandewater/ALOTT_MEDS) (a configuration-only MEDS-Extract 0.7
ETL, pinned to its PyPI release in `requirements.txt`) transforms the EMR tables of the PhysioNet
release into MEDS; the telemetry is out of scope. There is no public demo, so only the full-data
pipeline is exposed. Version 0.0.1 includes
[ALOTT_MEDS#2](https://github.com/rvandewater/ALOTT_MEDS/pull/2) (MEDS-Extract 0.7.1, aligned with
the published 1.0.0 schema).[2]

## Sources

1. [ALOTT v1.0.0 on PhysioNet](https://physionet.org/content/alott/1.0.0/)
2. [ALOTT-MEDS ETL](https://github.com/rvandewater/ALOTT_MEDS)
