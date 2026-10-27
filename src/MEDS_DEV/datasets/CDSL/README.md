# COVID Data for Shared Learning (CDSL)

## Description

COVID Data for Shared Learning (CDSL) is a multimodal database of de-identified medical data from
4,479 patients hospitalized with confirmed or suspected COVID-19 in the Spanish HM Hospitales group
(2019-12-26 to 2021-02-13). It provides demographic, diagnostic, clinical and treatment tables, and
chest X-ray / CT images. MEDS-DEV uses the tabular data and the DICOM metadata, not the images.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/covid-data-shared-learning/1.0.0/):

- **Access Policy**: Contributor review
- **License (for files)**: PhysioNet Contributor Review Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Contributor Review Health Data Use Agreement Version 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.

## Supported Tasks

- `mortality/in_icu/first_24h`: supported. There is no `MEDS_DEATH`; death is only the discharge
    destination, so `predicates.yaml` overrides the task's `death` with `HOSPITAL_DISCHARGE//Death`,
    timed at hospital discharge. For most ICU deaths that falls before the last ICU discharge.
- The six blood `abnormal_lab/*/first_24h` tasks: supported. Labs are already in the tasks' units.
    Bicarbonate exists only as blood-gas HCO3. There is no birth event (only age at admission), so
    the age >= 18 window cannot exclude the small share of subjects younger than 18.
- `abnormal_lab/vital/hypotension/first_24h`: not supported. Vitals have systolic/diastolic only.

These tasks are not yet listed in their `supported_datasets`; that follows in a separate PR once
all four local datasets (Zigong, PICdb, ALOTT, CDSL) are registered, to avoid conflicting edits.

## MEDS Transformation

[`CDSL-MEDS`](https://github.com/rvandewater/CDSL_MEDS) (a configuration-only MEDS-Extract 0.7 ETL,
not on PyPI at a version with the `MEDS_extract-CDSL` command, so `requirements.txt` pins the
0.0.3 tag) transforms the PhysioNet release into MEDS.
Three CDSL files are Latin-1 encoded, so the build downloads first and then runs
`MEDS_extract-CDSL`, which stages a UTF-8 view before extraction. There is no public demo, so only
the full-data pipeline is exposed. The pin is on
[CDSL_MEDS#2](https://github.com/rvandewater/CDSL_MEDS/pull/2), which introduces
`MEDS_extract-CDSL`; re-pin to `main` once that is merged.[2]

## Sources

1. [CDSL v1.0.0 on PhysioNet](https://physionet.org/content/covid-data-shared-learning/1.0.0/)
2. [CDSL-MEDS ETL](https://github.com/rvandewater/CDSL_MEDS)
