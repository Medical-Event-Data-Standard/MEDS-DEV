# Paediatric Intensive Care (PIC) Database

## Description

The Paediatric Intensive Care (PIC) database is a de-identified, paediatric-specific critical-care
database of 12,881 neonatal and paediatric patients and 13,449 hospital admissions at the Children's
Hospital of Zhejiang University School of Medicine (2010–2018). It follows the MIMIC structure:
admissions, ICU stays, laboratory and chart events, inputs and outputs, prescriptions, microbiology,
diagnoses and surgery records.[1][2]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/picdb/1.1.0/):

- **Access Policy**: Credentialed access
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement Version 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.

## Supported Tasks

Extracted on the full 1.1.0 release:

- `tasks/mortality/in_icu/first_24h.yaml`: ICU stays carry their unit (`ICU_ADMISSION//<unit>` for CICU,
    General ICU, NICU, PICU and SICU), and `MEDS_DEATH` coincides with the last ICU discharge for 968 of the
    971 deaths. Almost a quarter of the ICU stays start in the NICU; a variant without them may be worth a
    separate task.

The `abnormal_lab` tasks are not supported, although they extract without errors. They exclude patients aged
18 or younger and use adult thresholds, and PIC has no admission at 18 or older. Their only rows come from 68
admissions of newborns recorded up to a day before the recorded time of birth, which the age window does not
catch. The lab codes for a paediatric variant are creatinine `LAB//5041//μmol/L` and `LAB//5032//μmol/L`
(LOINC 2160-0), sodium `LAB//5230//mmol/L` (whole blood, LOINC 2947-0), bicarbonate `LAB//5248//mmol/L` and
`LAB//5224//mmol/L` (blood gas), hemoglobin `LAB//5099//g/L` (LOINC 718-7) and `LAB//5257//g/L` (blood gas),
WBC `LAB//5141//×10^9/L` (LOINC 26464-8) and platelets `LAB//5129//×10^9/L` (LOINC 777-3). There is no ICU
mean arterial pressure: the chart data has only systolic and diastolic pressure, and MAP is recorded only
during surgery (`SURGERY_VITAL//SV5`, `SURGERY_VITAL//SV12`).

PICdb has no demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`PICdb-MEDS`](https://github.com/rvandewater/PICdb_MEDS) is a pure-config
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.7 pipeline, registered as `spec=PICdb` for
`meds-extract-run`. There is no public demo, so only `build_full` is provided.[3] `requirements.txt` pins
commit `2cbffc3` of its `main` branch: the 0.0.1 release on PyPI (and the 0.0.2 tag) does not ship
`event_configs.yaml`, so its `spec=PICdb` entry point cannot load. That commit ships it and adds a
description for every code in `metadata/codes.parquet`. Notable properties of the conversion:

- **Dates are shifted** 50–100 years into the future per patient, so only time differences within one
    subject carry meaning.
- **Admissions and stays.** `HOSPITAL_ADMISSION//<department>` and `HOSPITAL_DISCHARGE//<department>` bound
    each hospital admission, and `ICU_ADMISSION//<unit>` and `ICU_DISCHARGE//<unit>` each ICU stay.
- **Birth and death** are `MEDS_BIRTH` and `MEDS_DEATH`, so the tasks' default predicates apply.
- **Labs** are `LAB//<ITEMID>//<unit>`, named in `metadata/codes.parquet` with the `LOINC/` parents of
    `D_LABITEMS`. Chart events are `CHART//<ITEMID>//<unit>`.

## Sources

1. [PIC database v1.1.0 on PhysioNet](https://physionet.org/content/picdb/1.1.0/)
2. [Zeng et al., PIC, a paediatric-specific intensive care database, Scientific Data 2020](https://doi.org/10.1038/s41597-020-0355-4)
3. [PICdb-MEDS ETL](https://github.com/rvandewater/PICdb_MEDS)
