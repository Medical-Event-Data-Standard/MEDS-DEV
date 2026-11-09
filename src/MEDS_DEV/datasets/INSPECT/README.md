# INSPECT: Integrating Numerous Sources for Prognostic Evaluation of Clinical Timelines

## Description

INSPECT is a multimodal dataset from Stanford Medicine of 19,402 patients with 23,248 CT pulmonary
angiography (CTPA) studies performed to diagnose pulmonary embolism. It pairs the CT images and radiology
report impressions with each patient's longitudinal structured EHR data, released as STARR-OMOP tables
(Stanford's research data repository in the OMOP Common Data Model).[1][2] MEDS-DEV uses only the
structured EHR modality.

## Access Requirements

Taken from the [INSPECT website](https://som-shahlab.github.io/inspect-website/) and
[Stanford AIMI](https://aimi.stanford.edu/datasets/inspect-Multimodal-Dataset-for-Pulmonary-Embolism-Diagnosis-and-Prognosis):

- **Access Policy**: The de-identified dataset is available under a data use agreement.[1][3]
- **Permitted use**: Non-commercial research use only.[1][3]
- **Distribution**: The EHR tables are distributed through Stanford's Redivis platform; the CT images
    through the Stanford AIMI shared datasets portal.[1][3]
- **Dataset DOI**: [10.71718/aqrb-et67](https://doi.org/10.71718/aqrb-et67).[3]

## Supported Tasks

No MEDS-DEV task lists INSPECT in its `supported_datasets` yet. Every current task excludes stays with a
hospital or ICU discharge shortly after admission, and this conversion has no discharge events (see below), so
`predicates.yaml` leaves `hospital_discharge` and `icu_discharge` undefined rather than approximating them.

## MEDS Transformation

The INSPECT EHR data is distributed in OMOP form. The predicates target a conversion of the INSPECT STARR-OMOP
release with [`meds_etl`](https://github.com/Medical-Event-Data-Standard/meds_etl)'s `meds_etl_omop` (version
`0.3.9.dev11+gba0eec1`, MEDS 0.3.3), which prefers source concepts over standard ones and writes codes as
`<vocabulary_id>/<concept_code>`, e.g. `LOINC/2951-2`. They do not match a conversion with MEDS-Extract, which
writes codes such as `LOINC//2951-2` and adds `//start` and `//end` events. `build_full` is not automated
because the conversion has not been verified against a published `meds_etl` release, so convert the download
yourself and pass the MEDS directory as `dataset_dir`. The conversion does not write
`metadata/subject_splits.parquet`, so add one before training models.

The predicates were chosen from a privacy-preserving code summary made with
[suMEDS](https://github.com/rvandewater/suMEDS) (codes seen in at least 20 subjects, with per-code and per-unit
value statistics), without inspecting patient-level data. Notable properties of the conversion:

- **Hospital admissions** are the `visit_occurrence` events, coded with Stanford source visit concepts
    `STANFORD_VISIT/<patient class>|<admission type>|<encounter type>`. `hospital_admission` matches hospital
    encounters with an inpatient patient class (`Inpatient`, `Private (Gen/Acute) (I)`, `Ward (Gen/Acute) (I)`,
    `Intensive Care (IC)`, `Surgery Admit`) for any admission type. Observation, pre-admission, skilled-nursing,
    and historical (legacy-system) encounters are excluded, as are appointments, anesthesia records, and lab
    draws recorded under an inpatient class.
- **ICU admissions** are `visit_detail` unit segments with the standard concept `Visit/OMOP4822460` (OMOP
    concept 32037, "Intensive Care"). Several segments can belong to one ICU stay. `CMS Place of Service/OMOP4822038`
    ("Inpatient Cardiac Care Facility") is not counted as ICU care.
- **No discharge events.** `meds_etl.omop` keeps visit end times only in the `end` column of the visit's start
    event, which ACES can't use, and writes a separate end-of-visit event only from `discharged_to_concept_id`,
    for which the conversion has no events.
- **Birth and death** are `MEDS_BIRTH` and `MEDS_DEATH`, so the tasks' default predicates apply.
- **Labs and vitals** use LOINC codes measured directly in blood, serum, or plasma, with units equivalent to
    the task thresholds: creatinine `LOINC/2160-0`; sodium `LOINC/2951-2`, `LOINC/2947-0`; bicarbonate as total
    CO2 `LOINC/2028-9`; hemoglobin `LOINC/718-7`, `LOINC/30313-1`; WBC `LOINC/20584-9`; platelets `LOINC/777-3`;
    and mean blood pressure `LOINC/8478-0`. `LOINC/6690-2` (leukocytes) is excluded because part of its values
    are reported per uL rather than 10^3/uL.

A conversion that emits visit-end events would support the discharge-based tasks, but it needs its own
predicates.

## Sources

1. [INSPECT website](https://som-shahlab.github.io/inspect-website/)
2. [INSPECT paper (arXiv:2311.10798)](https://arxiv.org/abs/2311.10798), NeurIPS 2023 Datasets and Benchmarks
    Track
3. [INSPECT on Stanford AIMI](https://aimi.stanford.edu/datasets/inspect-Multimodal-Dataset-for-Pulmonary-Embolism-Diagnosis-and-Prognosis)
4. [INSPECT benchmark code](https://github.com/som-shahlab/INSPECT_public)
