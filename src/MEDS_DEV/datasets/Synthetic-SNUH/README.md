# Synthetic-SNUH

## Description

Synthetic-SNUH v4 holds synthetic electronic health records for 10,000 virtual patients modelled on Seoul
National University Hospital (SNUH), 2021–2025, as OMOP CDM 5.4 tables (CSV, Parquet) and HL7 FHIR R4
resources (KR Core 1.0.2). It was generated only from anonymised aggregate statistics of the hospital's OMOP
CDM and contains no real patient record. It has no clinical notes, vital signs, allergies, immunisations,
imaging or pathology, and is intended for building and testing software and AI agents, not for clinical
inference.[1] MEDS-DEV uses version 4.0.0.

## Access Requirements

Taken from [KHDP](https://khdp.net/database/data-search-detail/synthetic-snuh?version=4.0.0):

- **Access Policy**: Open access on KHDP, the Korean Health Data Platform
- **License (for files)**: CC BY-NC 4.0; the OMOP vocabulary concepts remain subject to their own licences

Download the OMOP CDM Parquet tables from KHDP and pass their directory as `raw_input_dir`:

```bash
meds-dev-dataset dataset=Synthetic-SNUH output_dir=$DATASET_DIR raw_input_dir=$PARQUET_DIR
```

## Supported Tasks

None of the current tasks:

- `tasks/mortality/in_icu/first_24h.yaml` and
    `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml` follow an ICU stay. The export has
    no `visit_detail` rows and no care sites, so ICU stays can't be identified, and `icu_admission` and
    `icu_discharge` are undefined.
- `tasks/abnormal_lab/vital/hypotension/first_24h.yaml` needs blood pressure, which the dataset doesn't
    record.
- The other abnormal-lab tasks start at a hospital admission and label a lab on the day after the first 24
    hours. Synthetic-SNUH places nearly every inpatient lab on the day of admission: of the 795 creatinine
    results within the 1,397 inpatient stays longer than two days, 786 are on the admission day and one is
    two days later (hemoglobin: 799 of 812, and two). Each of these tasks extracts 0 to 2 samples.

The predicates the tasks use are defined anyway, except where the data can't support them.

## MEDS Transformation

[`OMOP_MEDS`](https://github.com/rvandewater/OMOP_MEDS) converts OMOP CDM 5.3–5.5 into MEDS with
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract), registered as `spec=OMOP`.[2] This dataset needs
[rvandewater/OMOP_MEDS#43](https://github.com/rvandewater/OMOP_MEDS/pull/43), which `requirements.txt` pins
until it is released. Notable properties of the conversion:

- **No times.** The export fills every `*_date` column and leaves every `*_datetime` column empty, so each
    event is at the end of its date, 23:59:59, the latest time it can have happened. Events of the same code
    and value on the same day are kept once.
- **Codes** are `<vocabulary>//<concept code>` of the mapped (standard) concept, such as `LOINC//2160-0`, with
    `//start` and `//end` for visits (`Visit//IP`, `Visit//ER`, `Visit//OP`) and conditions. Units are not
    recorded.
- **No vocabulary relationships.** The export has no `concept_relationship` table, so `metadata/codes.parquet`
    describes each code from its concept but gives it no parent codes.
- **Birth and death** are `MEDS_BIRTH` (from year, month and day of birth) and `MEDS_DEATH` (48 subjects).

## Sources

1. Lee, [Synthetic-SNUH v4: synthetic OMOP CDM and KR Core FHIR records for 10,000 virtual
    patients](https://doi.org/10.23421/2026.03183), KHDP (2026)
2. [OMOP_MEDS ETL](https://github.com/rvandewater/OMOP_MEDS)
