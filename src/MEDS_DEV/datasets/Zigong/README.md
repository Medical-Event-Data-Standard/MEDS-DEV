# Zigong Fourth People's Hospital ICU Infection Database

## Description

The Zigong database is a de-identified critical-care database of 2,790 ICU patients with infection,
one hospital admission each, from Zigong Fourth People's Hospital in Sichuan, China. It covers
baseline characteristics, transfers, laboratory results, prescriptions, nursing charts, diagnoses,
and outcomes including follow-up vital status.[1][2] MEDS-DEV uses release 1.1.

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/icu-infection-zigong-fourth/1.1/):

- **Access Policy**: Credentialed access
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement Version 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the source files from PhysioNet. Set `DATASET_DOWNLOAD_USERNAME` and
`DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access before running it.

## Supported Tasks

Seven of the eight current tasks, each extracted on the full 1.1 release:

- `tasks/mortality/in_icu/first_24h.yaml`, for subjects admitted straight into an ICU department only
    (see below).
- `tasks/abnormal_lab/blood_chemistry/elevated_creatinine/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/hyponatremia/first_24h.yaml`
- `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/anemia/first_24h.yaml`
- `tasks/abnormal_lab/cbc/leukocytosis/first_24h.yaml`
- `tasks/abnormal_lab/cbc/thrombocytopenia/first_24h.yaml`

`tasks/abnormal_lab/vital/hypotension/first_24h.yaml` is not supported: the raw MAP column holds only
unit strings, and ACES cannot derive MAP from systolic and diastolic pressure.

Zigong has no demo, so the integration tests do not exercise these pairs.

## MEDS Transformation

[`Zigong-MEDS`](https://github.com/rvandewater/ZIGONG_MEDS) 0.3.0 is a pure-config
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.7 pipeline, registered as `spec=Zigong` for
`meds-extract-run`. Zigong has no public demo, so only `build_full` is provided.[3] Notable properties of
the conversion:

- **Dates are not real.** Every source time is an offset in hours from hospital admission, placed on a
    shared anchor (1970-01-01 00:00 = admission). Each subject has exactly one admission.
- **One admission per subject.** `HOSPITAL_ADMISSION` and `HOSPITAL_DISCHARGE` bound the stay, and
    `ICU_DISCHARGE` marks the end of the ICU stay. The release records no ICU admission time, and its
    transfer table repeats rows within a stay
    ([ZIGONG_MEDS#3](https://github.com/rvandewater/ZIGONG_MEDS/issues/3)). `icu_admission` is therefore the
    admission of subjects whose admission department is an ICU (EICU, ICU, RICU, SICU or one of the two NICUs),
    about half of the cohort, at hospital admission. Subjects transferred into an ICU later are not in the
    in-ICU mortality cohort.
- **Death** is `MEDS_DEATH`, so the tasks' default `death` predicate applies. `Death_Date` has day precision
    and includes deaths at follow-up after discharge. The in-ICU mortality target ends at ICU discharge, so
    follow-up deaths do not count, but a death dated on the day of ICU discharge counts as an ICU death.
- **Age, not birth.** There is no `MEDS_BIRTH`, only `AGE_AT_ADMISSION` in years. `birth` matches that event
    for subjects younger than 18, so the abnormal-lab tasks' exclusion of children still applies.
- **Labs** are `LAB//<panel>//<item>//<unit>` in SI units, so the creatinine (umol/L) and hemoglobin (g/L)
    thresholds are converted from the tasks' US units. Sodium is the serum electrolyte panel. Bicarbonate is
    serum total CO2 plus measured blood-gas bicarbonate. Blood-gas hemoglobin is left out, because two of its
    codes are labelled g/L but hold g/dL values.

## Sources

1. [Zigong ICU infection database v1.1 on PhysioNet](https://physionet.org/content/icu-infection-zigong-fourth/1.1/)
2. [Xu et al., Critical Care Database Comprising Patients With Infection, Frontiers in Public Health 2022](https://doi.org/10.3389/fpubh.2022.852410)
3. [Zigong-MEDS ETL](https://github.com/rvandewater/ZIGONG_MEDS)
