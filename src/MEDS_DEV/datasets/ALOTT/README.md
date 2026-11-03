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

The six blood `abnormal_lab` tasks, each extracted on the full 1.0.0 release:

- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`

Two caveats apply to all six. Labs carry only a result *date* and are placed at 23:59:59, so the tasks'
24 h windows act as calendar days: the input window holds the labs of the admission day and the target
window those of the next day. The release has no birth date or age, so the tasks' adult filter excludes
no one.

Not supported:

- `mortality/in_icu/first_24h`: the release records no deaths, and no discharge destination marks one, so
    every label would be False. The ICU predicates are defined only because metabolic acidosis excludes
    stays with an ICU discharge in its first 48 h.
- `abnormal_lab/vital/hypotension/first_24h`: the EMR flowsheet has no blood pressure.

ALOTT has no demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`ALOTT-MEDS`](https://github.com/rvandewater/ALOTT_MEDS) 0.0.1, pinned to its PyPI release in
`requirements.txt`, is a configuration-only [MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.7
pipeline, registered as `spec=ALOTT` for `meds-extract-run`. It transforms the EMR tables of the PhysioNet
release into MEDS; the telemetry is out of scope. There is no public demo, so only `build_full` is provided.
Version 0.0.1 includes [ALOTT_MEDS#2](https://github.com/rvandewater/ALOTT_MEDS/pull/2) (MEDS-Extract
0.7.1, aligned with the published 1.0.0 schema).[2] Notable properties of the conversion:

- **Dates are shifted** by a random offset of up to 180 days in either direction per patient; the time of
    day is kept.
- **Admissions** are `HOSPITAL_ADMISSION//<type>//<source>` and `HOSPITAL_DISCHARGE//<destination>`. ICU
    stays are `ICU_ADMISSION` and `ICU_DISCHARGE`; the release does not say which unit.
- **No birth or death.** There is no `MEDS_BIRTH` or `MEDS_DEATH` event.
- **Labs** are `LAB//RESULT//<panel>//<component>`, timed at the end of the result date. The code carries
    no unit; the values are in US units (mg/dL, mmol/L, g/dL, K/uL). A chemistry panel reports each analyte
    under one of two component names, `BKR <ANALYTE>` or the plain name, and total CO2 as `CARBON DIOXIDE`
    or `CARBON DIOXIDE (CO2)`. The predicates list both, for every panel seen in at least 20 subjects.

## Sources

1. [ALOTT v1.0.0 on PhysioNet](https://physionet.org/content/alott/1.0.0/)
2. [ALOTT-MEDS ETL](https://github.com/rvandewater/ALOTT_MEDS)
