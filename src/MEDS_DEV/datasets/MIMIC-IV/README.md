# MIMIC-IV: Medical Information Mart for Intensive Care IV

## Description

MIMIC-IV is a large deidentified dataset of patients admitted to the emergency department or an intensive
care unit at the Beth Israel Deaconess Medical Center in Boston, MA, between 2008 and 2022. It contains
data for over 65,000 patients admitted to an ICU and over 200,000 patients admitted to the emergency
department.[1][2] Its `hosp` module comes from the hospital-wide EHR and its `icu` module from the
MetaVision ICU clinical information system. As of v3.0, PhysioNet counts 364,627 unique individuals with
546,028 hospitalizations and 94,458 ICU stays. MEDS-DEV uses release 3.1 (October 2024), which fixes lab
`itemid`s that changed unintentionally in 3.0 and removes two `subject_id`s missing from `patients`.

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/mimiciv/3.1/):

- **Access Policy**: Only credentialed users who sign the DUA can access the files
- **License (for files)**: PhysioNet Credentialed Health Data License 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the release from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it, or pass an
existing download as `raw_input_dir`.

The [MIMIC-IV demo](https://physionet.org/content/mimic-iv-demo/2.2/) (version 2.2, 100 patients) is open
access under the Open Data Commons Open Database License 1.0, so the demo build needs no credentials.[3]

## Supported Tasks

Every current task:

- `tasks/mortality/in_icu/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`
- `tasks/abnormal_lab/vital/hypotension/first_24h.yaml`

The integration tests and CI run every task and model on the demo build.

## MEDS Transformation

[`MIMIC-IV-MEDS`](https://github.com/Medical-Event-Data-Standard/MIMIC_IV_MEDS) 0.1.0 provides the
`MEDS_extract-MIMIC_IV` command, which downloads the release, runs a pre-MEDS step over the raw tables and
then builds the MEDS dataset with MEDS-Transforms.[4] `build_demo` passes `do_demo=True`, which builds the
open demo instead of the full release. Notable properties of the conversion:

- **Visits.** `HOSPITAL_ADMISSION//<admission type>//<admission location>` and
    `HOSPITAL_DISCHARGE//<discharge location>` mark hospital stays, `ICU_ADMISSION//<first care unit>` and
    `ICU_DISCHARGE//<last care unit>` mark ICU stays, and `ED_REGISTRATION` and `ED_OUT` mark the emergency
    department visit before an admission. The admission and discharge predicates match these by prefix.
- **Measurements** keep MIMIC-IV's `itemid` and unit. Hospital lab results (`hosp/labevents`) are
    `LAB//RESULT//<itemid>//<unit>`, and values charted in the ICU (`icu/chartevents`), including vital
    signs, are `LAB//<itemid>//<unit>`. Each lab predicate therefore combines the hospital lab with the
    matching ICU chart item, and matches only the unit listed. The abnormal thresholds are in the units of
    the tasks, so none is converted.
- **Birth and death** are `MEDS_BIRTH` and `MEDS_DEATH`, so the tasks' default predicates apply. The birth
    year is `anchor_year - anchor_age`, so births have year precision, and patients over 89 have an
    `anchor_age` of 91. A death is placed at the earliest in-hospital `deathtime`, or else at the date of
    death in `patients`, which also covers deaths up to one year after hospital or ED discharge from state
    records.
- **Dates are shifted** into 2100–2200 by one random offset per patient, which keeps the order and spacing
    of each patient's events.

| Predicate     | Hospital lab (`LAB//RESULT//…`)     | ICU chart (`LAB//…`)                                                 | Abnormal    |
| ------------- | ----------------------------------- | -------------------------------------------------------------------- | ----------- |
| `creatinine`  | 50912, 52546 (creatinine, mg/dL)    | none                                                                 | > 1.3 mg/dL |
| `sodium`      | 50983, 52623 (sodium, mEq/L)        | 220645 (sodium, serum)                                               | < 135 mEq/L |
| `bicarbonate` | 50882 (bicarbonate, mEq/L)          | 227443 (HCO3, serum)                                                 | < 22 mEq/L  |
| `hemoglobin`  | 50811 (hemoglobin, blood gas, g/dL) | 220228 (hemoglobin, g/dl)                                            | < 13 g/dL   |
| `wbc`         | 51300 (WBC count, K/uL)             | 220546 (WBC)                                                         | > 11 K/uL   |
| `platelets`   | 51265 (platelet count, K/uL)        | 227457 (platelet count)                                              | < 150 K/uL  |
| `map`         | none                                | 220052 (arterial), 220181 (non-invasive), 225312 (ART) mean BP, mmHg | < 65 mmHg   |

The item labels are those of the open demo's `d_labitems` and `d_items`.

## Sources

1. [MIMIC-IV 3.1 on PhysioNet](https://physionet.org/content/mimiciv/3.1/)
    ([doi:10.13026/kpb9-mt58](https://doi.org/10.13026/kpb9-mt58))
2. Johnson et al.,
    [MIMIC-IV, a freely accessible electronic health record dataset](https://doi.org/10.1038/s41597-022-01899-x),
    Scientific Data 10, 1 (2023)
3. [MIMIC-IV demo 2.2 on PhysioNet](https://physionet.org/content/mimic-iv-demo/2.2/)
    ([doi:10.13026/dp1f-ex47](https://doi.org/10.13026/dp1f-ex47))
4. [MIMIC-IV-MEDS ETL](https://github.com/Medical-Event-Data-Standard/MIMIC_IV_MEDS)
    ([doi:10.5281/zenodo.17535579](https://doi.org/10.5281/zenodo.17535579))
