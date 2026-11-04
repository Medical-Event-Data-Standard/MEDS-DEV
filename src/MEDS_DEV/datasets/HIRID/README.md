# HiRID: a high time-resolution ICU dataset

## Description

HiRID holds 33,905 admissions to the Department of Intensive Care Medicine of the Bern University Hospital,
Switzerland, an interdisciplinary 60-bed unit, between January 2008 and June 2016. It contains de-identified
demographics and 681 routinely collected physiological variables, diagnostic test results and treatment
parameters, with bedside measurements recorded as often as every two minutes. It was developed by the Swiss
Federal Institute of Technology (ETH) Zürich and the ICU.[1][2] MEDS-DEV uses release 1.1.1.

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/hirid/1.1.1/):

- **Access Policy**: Only credentialed users who sign the DUA can access the files, and each study must be
    reviewed by the HiRID contributors
- **License (for files)**: PhysioNet Contributor Review Health Data License 1.5.0
- **Data Use Agreement**: PhysioNet Contributor Review Health Data Use Agreement 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the three release files it reads (about 7 GB) from PhysioNet. Set
`DATASET_DOWNLOAD_USERNAME` and `DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access
before running it. To reuse an existing download, pass its directory as `raw_input_dir`: files whose checksum
matches PhysioNet's manifest are not downloaded again, although the credentials are still needed to fetch the
manifest.

## Supported Tasks

Every current task, each extracted on the full 1.1.1 release:

- `tasks/mortality/in_icu/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`
- `tasks/abnormal_lab/vital/hypotension/first_24h.yaml`

The hospital-level tasks use the ICU stay (see below), so they predict from the first 24 hours of the ICU stay
and require a stay of at least 48 hours.

HiRID has no demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`HIRID-MEDS`](https://github.com/rvandewater/HIRID_MEDS) is a pure-config
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) pipeline, registered as `spec=HIRID` for
`meds-extract-run`.[3] HiRID has no public demo, so only `build_full` is provided. The build sets
`POLARS_ENGINE_AFFINITY=streaming`, which keeps it under 10 GB of memory; without it, subject sharding runs out
of memory on a 24 GB machine. Extracts made with HIRID-MEDS 0.0.1–0.0.4 duplicate, mislabel and drop some observation events, so they
should be rebuilt. Notable properties of the conversion:

- **ICU stays only.** Each subject is one ICU admission. `HOSPITAL_ADMISSION` is the ICU admission time and
    `HOSPITAL_DISCHARGE` is the time of the subject's last observation, since HiRID records no discharge time.
    The ETL keeps these names from its earlier releases. HiRID records no hospital admission or discharge, so
    the hospital-level tasks use the ICU stay, as they do for SICdb.
- **Dates are shifted** into the future, keeping the order and spacing of events within a subject.
- **Birth and death** are `MEDS_BIRTH` and `MEDS_DEATH`, so the tasks' default predicates apply. The birth is
    estimated from the age at admission, which HiRID records in 5-year bins from 20 to 90, so it can be off by
    up to about 5 years. `MEDS_DEATH` is placed at the last observation when the discharge status is `dead`,
    which makes it a death in the ICU. It coincides with `HOSPITAL_DISCHARGE`.
- **Observations** are `OBSERVATION//<variable name>//<unit>`, using HiRID's variable reference. Lab values
    are in SI units, so two thresholds are converted: creatinine to 114.92 µmol/L (1.3 mg/dL) and hemoglobin to
    130 g/L (13 g/dL). HiRID has no serum bicarbonate, so `bicarbonate` uses arterial blood-gas bicarbonate. The
    LOINC codes of the lab variables come from the suMEDS rules file that HIRID-MEDS ships.
- **Mean arterial pressure** combines the invasive and non-invasive readings. The invasive signal is recorded
    as often as every two minutes, so `abnormally_low_map` flags a single reading below 65 mmHg. Few stays have
    no such reading in their first 24 hours, so the hypotension cohort is small.

## Sources

1. [HiRID 1.1.1 on PhysioNet](https://physionet.org/content/hirid/1.1.1/)
    ([doi:10.13026/nkwc-js72](https://doi.org/10.13026/nkwc-js72))
2. Hyland et al.,
    [Early prediction of circulatory failure in the intensive care unit using machine learning](https://doi.org/10.1038/s41591-020-0789-4),
    Nature Medicine 26, 364–373 (2020)
3. [HIRID-MEDS ETL](https://github.com/rvandewater/HIRID_MEDS)
