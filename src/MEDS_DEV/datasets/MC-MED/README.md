# Multimodal Clinical Monitoring in the Emergency Department (MC-MED)

## Description

MC-MED holds 118,385 adult emergency department (ED) visits by 70,545 patients at Stanford Health Care
between 2020 and 2022. For each visit it contains demographics, triage, the ED course and dispositions, the
primary ED diagnoses, orders and medication administrations, laboratory results, radiology report
impressions, charted and monitor vital signs, past medical history, and home medications, together with
continuous ECG, photoplethysmography and respiration waveforms.[1][2] MEDS-DEV uses release 1.0.1.

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/mc-med/1.0.1/):

- **Access Policy**: Only credentialed users who sign the DUA can access the files
- **License (for files)**: PhysioNet Credentialed Health Data License 1.5.0
- **Data Use Agreement**: PhysioNet Credentialed Health Data Use Agreement 1.5.0
- **Required training**: CITI Data or Specimens Only Research

The ETL downloads the tabular files of the release from PhysioNet (not the waveforms). Set
`DATASET_DOWNLOAD_USERNAME` and `DATASET_DOWNLOAD_PASSWORD` to the credentials of an account with access
before running it.

## Supported Tasks

None of the current tasks. Every one of them needs a hospital or ICU stay, and MC-MED records the ED visit
only:

- `tasks/mortality/in_icu/first_24h.yaml` and
    `tasks/abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h.yaml` follow an ICU stay. MC-MED
    identifies the 2,766 visits (2.3%) admitted from the ED to the ICU, so `icu_admission` is
    `ED_DISPOSITION//ICU`, the disposition decision. But it records no ICU discharge time and no labs or vital
    signs after ED departure, so `icu_discharge` is undefined and the tasks cannot be extracted.
- The other abnormal-lab tasks and `tasks/abnormal_lab/vital/hypotension/first_24h.yaml` start at the hospital
    admission and label a measurement 24 to 48 hours later. MC-MED's labs and vital signs end at ED
    departure, so only patients still boarding in the ED more than a day after their admission order
    qualify. On the full release each of these tasks extracts fewer than 100 samples from about 48,000
    admissions, too few and too unusual a group to evaluate on.

The predicates the tasks use are defined anyway, so ED-specific tasks can be added later.

## MEDS Transformation

[`MC-MED-MEDS`](https://github.com/rvandewater/MC_MED_MEDS) is a pure-config
[MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) pipeline, registered as `spec=MC-MED`. It is
run with [suMEDS](https://github.com/rvandewater/SumMEDS)' `suMEDS-extract`, which runs `meds-extract-run`
and then adds the official ICD-10-CM and ICD-9-CM titles and parents to `metadata/codes.parquet`. MC-MED has
no public demo, so only `build_full` is provided.[3] Notable properties of the conversion:

- **Dates are shifted** per patient into 2150–2350 by the dataset authors, keeping the season, so only
    time differences within one subject carry meaning.
- **One visit is one ED encounter**, from `ED_ARRIVAL//<means of arrival>` to `ED_DEPARTURE`, and every
    visit-scoped event carries the visit's `CSN` in a `csn` column. Triage has no time of its own and is placed
    at arrival.
- **Hospital and ICU admission, and discharge.** `HOSPITAL_ADMISSION//<service>` is the admission order of
    a visit admitted from the ED, and `ED_DISPOSITION//ICU` marks the decision to admit it to the ICU, a median
    of 2.3 h before the patient leaves the ED. MC-MED has no discharge time, so `HOSPITAL_DISCHARGE//<disposition>` is
    reconstructed from the whole-day hospital length of stay, never earlier than ED departure. It is
    accurate to about a day.
- **Birth and death.** There is no `MEDS_BIRTH`: MC-MED gives only an age perturbed by up to 2 years at each
    visit, as an `AGE` event. `MEDS_DEATH` marks in-hospital deaths only (a discharge disposition of
    `Expired`), at the reconstructed discharge time, so a subject without one is not known to be alive.
- **Labs** are `LAB//<component name>//<unit>`, from the ED visit only, with the parsed value as
    `numeric_value` and the raw result as `text_value`. Vital signs are `VITAL//<measure>//{Chart,Monitor}`;
    monitor values are means over the preceding minute.
- **Diagnoses** are dotted ICD codes: `ED_DIAGNOSIS//ICD10CM//<code>` and `ED_DIAGNOSIS//ICD9CM//<code>`
    for the visit, and `PMH//ICD10CM//<code>` and `PMH//ICD9CM//<code>` for past medical history.

## Sources

1. [MC-MED 1.0.1 on PhysioNet](https://physionet.org/content/mc-med/1.0.1/)
    ([doi:10.13026/wvyw-g663](https://doi.org/10.13026/wvyw-g663))
2. Kansal et al.,
    [MC-MED, multimodal clinical monitoring in the emergency department](https://doi.org/10.1038/s41597-025-05419-5),
    Scientific Data 12 (2025)
3. [MC-MED-MEDS ETL](https://github.com/rvandewater/MC_MED_MEDS)
