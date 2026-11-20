# Synthetic K-MIMIC (SYN-ICU)

## Description

Synthetic K-MIMIC (SYN-ICU) is a synthetic intensive care dataset published by the Korea Health Data
Platform (KHDP). It was generated from the real-world ICU records of Seoul National University Hospital and
follows the MIMIC-IV table layout: patients, admissions, transfers, ICU stays, diagnoses (KCD) and
procedures, laboratory results, medication administrations, and ICU chart, input, output and procedure
events.[1] The release holds 1,328 subjects, each with one hospital admission and one ICU stay.

## Access Requirements

- **Access Policy**: Distributed by KHDP to registered users whose data application is approved.[1]
- **Download**: KHDP has no download API. Download the release (15 `.xlsx` workbooks, `syn_patients.xlsx`
    and so on) by hand and pass the directory holding them as `raw_input_dir`.

## Supported Tasks

Extracted on the full SYN-ICU release with K-MIMIC-MEDS (one sample per subject in every task):

| Task                                                                    | Samples | Positives |
| ----------------------------------------------------------------------- | ------: | --------: |
| `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml` |     204 |        67 |
| `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`  |     191 |        81 |
| `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`                          |     135 |       129 |
| `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`                    |     204 |        85 |
| `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`                |     194 |        83 |

The predicates also define everything the other three tasks need, and they extract, but each has fewer than
20 positive labels, too few to evaluate on. K-MIMIC is therefore not listed for them:

- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml` (250 samples)
- `tasks/abnormal_lab/vital/hypotension/first_24h.yaml` (421 samples)
- `tasks/mortality/in_icu/first_24h.yaml` (189 samples)

K-MIMIC has no public demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`K-MIMIC-MEDS`](https://github.com/rvandewater/K_MIMIC_MEDS) is a config-only
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.8 pipeline, registered as `spec=K-MIMIC`, with
one registered pre-stage that stages the release's Excel workbooks as parquet.[2] It supersedes the first
MEDS conversion of this dataset, [K-MIMIC-MEDS by Choi et al.](https://github.com/ji-ch01/K-MIMIC-MEDS),
a standalone pandas pipeline.[3] Its codes follow MIMIC-IV-MEDS:

- **Admissions and ICU stays:** `HOSPITAL_ADMISSION//…`, `HOSPITAL_DISCHARGE//…`, `ICU_ADMISSION//…`
    and `ICU_DISCHARGE//…`.
- **Birth and death** are `MEDS_BIRTH` (year only, from `anchor_year - anchor_age`) and `MEDS_DEATH`
    (the in-hospital death time), so the tasks' default predicates apply.
- **Labs** are `LAB//RESULT//<itemid>//<unit>`, timed at `storetime`. The predicates' item ids were chosen
    from the release's lab dictionary and checked against each item's unit and value distribution. Every unit
    equals the task's threshold unit. `bicarbonate` combines serum total CO2 and blood-gas HCO3.
- **Vital signs** are `ICU_CHART//<itemid>//<unit>`. `map` combines the two monitor channels that chart a
    mean arterial pressure in mmHg.
- **Diagnoses** are timed at hospital discharge, not as static codes, so they cannot leak into earlier
    prediction times.

### Data quality

The synthetic release has timing inconsistencies, which K-MIMIC-MEDS keeps as recorded:

- 11–19% of chart, lab, medication, fluid and procedure events fall after the hospital discharge time.
- Every deceased subject has events after death.
- 26 admissions are flagged as in-hospital deaths but have no death time; they carry no `MEDS_DEATH`.

The supported tasks exclude stays that end within 48 hours of the trigger, so their labels come from
measurements before discharge. The ETL's README documents the issues in full, with the measured rates.[2]

## Sources

1. [Synthetic K-MIMIC (SYN-ICU) on KHDP](https://khdp.net/database/data-search-detail/SYN-ICU)
2. [K-MIMIC-MEDS ETL](https://github.com/rvandewater/K_MIMIC_MEDS)
3. Choi et al., [K-MIMIC-MEDS](https://github.com/ji-ch01/K-MIMIC-MEDS), the first MEDS conversion of
    Synthetic K-MIMIC
