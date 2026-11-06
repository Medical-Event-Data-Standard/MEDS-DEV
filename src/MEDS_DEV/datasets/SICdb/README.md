# Salzburg Intensive Care database (SICdb)

## Description

The Salzburg Intensive Care database (SICdb) holds more than 27,000 intensive care admissions from four
ICUs at the University Hospital Salzburg, collected between 2013 and 2021. It covers general and surgical
intensive care, including data on the surgery preceding an admission, and contains case information,
diagnoses, laboratory results, medications, devices, and vital signs as both hourly aggregates and
minute-resolution signals.[1][2] MEDS-DEV uses release 1.0.8.

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/sicdb/1.0.8/):

- **Access Policy**: Only credentialed users who sign the DUA can access the files, and each study must be
    reviewed by the SICdb contributors
- **License (for files)**: PhysioNet Contributor Review Health Data License 1.5.0
- **Data Use Agreement**: PhysioNet Contributor Review Health Data Use Agreement 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the release from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it. To reuse an
existing download, pass its directory (the one holding `SHA256SUMS.txt`) as `raw_input_dir`: files whose
checksum matches PhysioNet's manifest are not downloaded again, although the credentials are still needed
to fetch the manifest.

## Supported Tasks

Every current task, each extracted on the full 1.0.8 release:

- `tasks/mortality/in_icu/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`
- `tasks/abnormal_lab/vital/hypotension/first_24h.yaml`

SICdb has no demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`SICdb-MEDS`](https://github.com/rvandewater/SICdb_MEDS) is a pure-config
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) pipeline, registered as `spec=SICdb` for
`meds-extract-run`. SICdb has no public demo, so only `build_full` is provided.[3] Notable properties of the
conversion:

- **Dates are not real.** SICdb gives offsets in seconds, not dates. Every patient's first admission is
    placed on 2017-07-02 and everything else keeps its offset from it, so only time differences within one
    subject carry meaning. The real admission year is kept as an `ADMISSION_YEAR//<year>` event.
- **One case is one ICU admission** with its preceding surgery, if any. `ADMISSION//<urgency>` opens the
    case and is used as the hospital admission, since SICdb records no hospital admission time. `ICU_ADMISSION` marks the first transfer to an intensive or intermediate care
    ward, and `DISCHARGE//<state>` closes the case on leaving the ICU. `HOSPITAL_DISCHARGE//<type>` is
    recorded to the day and placed at noon.
- **Birth and death** are `MEDS_BIRTH` and `MEDS_DEATH`, so the tasks' default predicates apply. The birth
    is estimated from the age at the first admission, which SICdb records in whole years and caps at 90.
    SICdb records a death only when it happens within a year of the admission.
- **Labs** are `LAB//<LaboratoryID>//<specimen>`, with the specimen `ARTERIAL` for blood-gas analyses and
    `UNSPEC` otherwise. Their names, units, and LOINC parent codes are in `metadata/codes.parquet`. SICdb has
    no serum bicarbonate, so `bicarbonate` uses blood-gas bicarbonate.
- **Vital signs** are `VITAL//<DataID>` and are hourly aggregates, so `abnormally_low_map` flags an hour
    whose mean pressure is below 65 mmHg rather than a single reading.

## Sources

1. [SICdb 1.0.8 on PhysioNet](https://physionet.org/content/sicdb/1.0.8/)
    ([doi:10.13026/8m72-6j83](https://doi.org/10.13026/8m72-6j83))
2. Rodemund et al.,
    [Harnessing Big Data in Critical Care: Exploring a New European Dataset](https://doi.org/10.1038/s41597-024-03164-9),
    Scientific Data 11, 320 (2024)
3. [SICdb-MEDS ETL](https://github.com/rvandewater/SICdb_MEDS)
