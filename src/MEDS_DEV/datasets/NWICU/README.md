# Northwestern ICU (NWICU) Database

## Description

The Northwestern ICU (NWICU) database is a de-identified critical-care database containing data from
more than 25,000 patients treated in the Northwestern Medicine health system from 2020 through 2022. It
retains the MIMIC-IV hospital and ICU module structure and includes demographics, admissions, laboratory
measurements, diagnoses, medication administration, ICU stays, charted observations, and procedures.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/nwicu-northwestern-icu/0.1.0/):

- **Access Policy**: Credentialed access
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement Version 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.[2]

## Supported Tasks

No MEDS-DEV tasks have yet been validated against NWICU.

## MEDS Transformation

[`NWICU-MEDS`](https://github.com/rvandewater/NWICU_MEDS) transforms the credentialed PhysioNet
release into MEDS. The MEDS-DEV recipe intentionally exposes only the full-data pipeline because NWICU
does not provide a public demo dataset.[2]

## Sources

1. [NWICU on PhysioNet](https://physionet.org/content/nwicu-northwestern-icu/0.1.0/)
2. [NWICU-MEDS ETL](https://github.com/rvandewater/NWICU_MEDS)

## Disclaimer

Refer to the data owners and the latest PhysioNet documentation when using NWICU. The dataset is intended
for research and education, not clinical care.
