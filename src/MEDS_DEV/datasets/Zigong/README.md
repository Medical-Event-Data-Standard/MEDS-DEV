# Zigong Fourth People's Hospital ICU Infection Database

## Description

The Zigong database is a de-identified critical-care database of 2,790 ICU patients with infection,
one hospital admission each, from Zigong Fourth People's Hospital in Sichuan, China. It covers
baseline characteristics, transfers, laboratory results, prescriptions, nursing charts, diagnoses,
and outcomes including follow-up vital status.[1][2]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/icu-infection-zigong-fourth/1.1/):

- **Access Policy**: Credentialed access
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement Version 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.

## Supported Tasks

- `abnormal_lab/blood_chemistry/{elevated_creatinine,hyponatremia,metabolic_acidosis}/first_24h` and
    `abnormal_lab/cbc/{anemia,leukocytosis,thrombocytopenia}/first_24h`: lab codes and units map
    cleanly. Creatinine (umol/L) and hemoglobin (g/L) thresholds are converted from the tasks' US
    units. There is no birth event (only age at admission), so the tasks' age >= 18 window cannot
    exclude the small share of subjects younger than 18.
- `mortality/in_icu/first_24h`: possible only for subjects admitted straight into an ICU department.
    The release has no ICU admission time, and its transfer table repeats rows within a stay
    ([ZIGONG_MEDS#3](https://github.com/rvandewater/ZIGONG_MEDS/issues/3)). Death dates have day
    precision.
- `abnormal_lab/vital/hypotension/first_24h`: not supported. The raw MAP column holds only unit
    strings, and ACES cannot derive MAP from systolic/diastolic pressure.

These tasks are not yet listed in their `supported_datasets`; that follows in a separate PR once
all four local datasets (Zigong, PICdb, ALOTT, CDSL) are registered, to avoid conflicting edits.

## MEDS Transformation

[`Zigong-MEDS`](https://github.com/rvandewater/ZIGONG_MEDS) (a configuration-only MEDS-Extract 0.7
ETL, pinned to its PyPI release in `requirements.txt`) transforms the credentialed PhysioNet
release into MEDS. There is no public demo, so only the full-data pipeline is exposed.[3]

## Sources

1. [Zigong ICU infection database v1.1 on PhysioNet](https://physionet.org/content/icu-infection-zigong-fourth/1.1/)
2. [Xu et al., Critical Care Database Comprising Patients With Infection, Frontiers in Public Health 2022](https://doi.org/10.3389/fpubh.2022.852410)
3. [Zigong-MEDS ETL](https://github.com/rvandewater/ZIGONG_MEDS)
