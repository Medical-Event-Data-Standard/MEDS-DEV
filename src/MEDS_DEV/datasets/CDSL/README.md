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

Every current task except hypotension, each extracted on the full 1.0.0 release:

- `tasks/mortality/in_icu/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`

`tasks/abnormal_lab/vital/hypotension/first_24h.yaml` is not supported: CDSL records systolic and diastolic
blood pressure but no mean arterial pressure. CDSL has no demo, so the integration tests do not exercise
these pairs.

## MEDS Transformation

[`CDSL-MEDS`](https://github.com/rvandewater/CDSL_MEDS) is a configuration-only
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.7 pipeline, registered as `spec=CDSL`.[2]
`requirements.txt` pins `CDSL-MEDS==0.0.1`, the newest code on PyPI: it was published from the `0.0.3` tag
after `0.0.2`, which is older code. Three CDSL files are Latin-1 encoded, so the build downloads first and
then runs `MEDS_extract-CDSL`, which stages a UTF-8 view of the download before extraction. There is no
public demo, so only `build_full` is provided. Notable properties of the conversion:

- **One hospital stay per subject.** `HOSPITAL_ADMISSION` and `HOSPITAL_DISCHARGE//<destination>` are
    recorded to the day and placed at midnight, so "the first 24 hours" of the abnormal-lab tasks is the
    admission day. `ICU_ADMISSION` and `ICU_DISCHARGE` carry a time of day.
- **Death** is only a discharge destination. There is no `MEDS_DEATH`, so `predicates.yaml` overrides the
    tasks' `death` with `HOSPITAL_DISCHARGE//Death`, timed at the (midnight) hospital discharge. For most
    ICU deaths that falls before the ICU discharge, so the in-ICU target window still sees it.
- **Age** is recorded in whole years at admission (`AGE_AT_ADMISSION`), and there is no `MEDS_BIRTH`. The
    abnormal-lab tasks exclude children by requiring no `birth` in the 18 years before admission, so
    `predicates.yaml` defines `birth` as an age below 18 at that admission. This excludes exactly the
    subjects younger than 18.
- **Labs** are `LAB//<item> -- <name>//<unit>` and are already in the tasks' units. Bicarbonate and total
    CO2 are reported only in blood-gas panels, so `bicarbonate` uses blood-gas HCO3.

## Sources

1. [CDSL v1.0.0 on PhysioNet](https://physionet.org/content/covid-data-shared-learning/1.0.0/)
    ([doi:10.13026/1176-6c44](https://doi.org/10.13026/1176-6c44))
2. [CDSL-MEDS ETL](https://github.com/rvandewater/CDSL_MEDS)
    ([doi:10.5281/zenodo.23676596](https://doi.org/10.5281/zenodo.23676596))
