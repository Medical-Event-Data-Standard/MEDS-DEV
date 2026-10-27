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

- `mortality/in_icu/first_24h`: well defined. ICU stays carry their unit (CICU, General ICU, NICU,
    PICU, SICU), and `MEDS_DEATH` coincides with the last ICU discharge for nearly all ICU deaths.
    Many subjects are neonates; a NICU-excluded variant may be worth a separate task.
- `abnormal_lab/*`: not supported. Every subject is under 18, so these tasks' age >= 18 window leaves
    an empty cohort, and their adult thresholds would not apply. The lab codes for a paediatric variant:
    creatinine `LAB//5041//μmol/L`, sodium `LAB//5230//mmol/L` (blood gas), bicarbonate
    `LAB//5248//mmol/L` / `LAB//5224//mmol/L`, hemoglobin `LAB//5099//g/L`, WBC `LAB//5141//×10^9/L`,
    platelets `LAB//5129//×10^9/L`. There is no ICU MAP (chart data has systolic/diastolic only).

These tasks are not yet listed in their `supported_datasets`; that follows in a separate PR once
all four local datasets (Zigong, PICdb, ALOTT, CDSL) are registered, to avoid conflicting edits.

## MEDS Transformation

[`PICdb-MEDS`](https://github.com/rvandewater/PICdb_MEDS) (a configuration-only MEDS-Extract 0.7
ETL; its PyPI release 0.0.1 does not ship the spec file, so `requirements.txt` pins a commit) transforms the credentialed PhysioNet
release into MEDS. There is no public demo, so only the full-data pipeline is exposed.[3]

## Sources

1. [PIC database v1.1.0 on PhysioNet](https://physionet.org/content/picdb/1.1.0/)
2. [Zeng et al., PIC, a paediatric-specific intensive care database, Scientific Data 2020](https://doi.org/10.1038/s41597-020-0355-4)
3. [PICdb-MEDS ETL](https://github.com/rvandewater/PICdb_MEDS)
