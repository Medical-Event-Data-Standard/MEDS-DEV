# EHRSHOT

## Description

A benchmark dataset of de-identified structured electronic health record data from Stanford Medicine containing longitudinal health records for 6,739 patients with 41.6 million coded clinical observations and 921,499 visits, designed for few-shot evaluation of foundation models on EHR data.[1][2]

## Access Requirements

Taken from [Stanford Shah Lab website](https://shahlab.stanford.edu/doku.php?id=ehrshot_license):

- **Access Policy**: Sign the EHRSHOT Credentialed Health Data License and Data Use Agreement[3][4]
- **License (for files)**: EHRSHOT Credentialed Health Data License Version 1.0 (modeled after Physionet Version 1.5.0)[3]
- **Data Use Agreement**: Agreement requires verified institutional affiliation and commitment to use data solely for lawful scientific research[5][3]
- **Required training**: Valid CITI training certification in human research subject protection and HIPAA regulations[4][3]
- **License Term**: 3 years from account creation date[3]
- **Code Sharing**: Agreement to contribute code associated with publications to open research repository[3]

## Supported Tasks

EHRSHOT includes 15 classification tasks organized into three categories as the benchmark dataset itself. However, here we use ACES-defined values to extract tasks from the dataset.

No MEDS-DEV task lists EHRShot in its `supported_datasets` yet. The current tasks exclude stays with a discharge
shortly after admission, which this release can't express (see below), so they can't be enabled for it as is.

## MEDS-transformation

EHRSHOT is available in three formats: Original (compatible with benchmark repository), MEDS (Medical Event Data Standard), and OMOP (full OMOP table dumps). The MEDS version contains the same exact data as the Original dataset but in MEDS-compatible format.[1]

### Which version `predicates.yaml` targets

The predicates target the **official MEDS release** (`EHRSHOT => MEDS ETL` 1.0, MEDS 0.3.3), with codes such as
`LOINC/2951-2`, `Visit/IP`, and `CARE_SITE/<id>`. They do not match a MEDS dataset converted from the OMOP
download with MEDS-Extract, which writes codes as `LOINC//2951-2` and conditions/visits with `//start` and
`//end` suffixes.

Notable properties of the official MEDS release:

- **No discharge events.** Visits are recorded only at their start (`Visit/IP`, `Visit/ER`, `Visit/ERIP`, ...),
    so `hospital_discharge` and `icu_discharge` are deliberately left undefined.
- **ICU stays can't be verified.** ICU care sites use the release's own care-site IDs, which differ from the
    OMOP `care_site` IDs, so the `icu_admission` IDs can't be checked against care-site names.
- **Birth and death** are `SNOMED/3950001` and `Condition Type/OMOP4822053` rather than `MEDS_BIRTH` and
    `MEDS_DEATH`; `predicates.yaml` overrides the tasks' `birth` and `death` predicates accordingly.
- **WBC:** `LOINC/6690-2` holds erythrocyte-scale values (MIL/uL); white-cell counts are under `LOINC/20584-9`.
- **Bicarbonate** uses total CO2 (`LOINC/2028-9`) and `LOINC/1959-6`; `LOINC/2021-4` is venous pCO2.

The OMOP-derived conversion has visit-end events, `MEDS_DEATH`, and care-site names, so it could support the
discharge- and ICU-based tasks, but it needs its own predicates and a reproducible build.

## Sources

1. [EHRSHOT Official Website](https://ehrshot.stanford.edu)
2. [EHRSHOT Research Paper](https://arxiv.org/html/2307.02028v3)
3. [GitHub Repository](https://github.com/som-shahlab/ehrshot-benchmark)
4. [Redivis Dataset Portal](https://redivis.com/datasets/53gc-8rhx41kgt)
5. [Stanford AIMI Shared Datasets](https://stanfordaimi.azurewebsites.net/datasets/54c5d2a1-ef39-489e-b5f8-8f9e27e9750b)
6. [EHRSHOT License Agreement](https://shahlab.stanford.edu/doku.php?id=ehrshot_license)

## Disclaimer

Please refer to the data owners and the most up-to-date information when using this dataset in your research. The EHRSHOT dataset has not been reviewed or approved by the Food and Drug Administration and is for non-clinical, research and education use only.[3]

[1](https://github.com/som-shahlab/ehrshot-benchmark)
[2](https://openreview.net/forum?id=CsXC6IcdwI)
[3](https://shahlab.stanford.edu/doku.php?id=ehrshot_license)
[4](https://redivis.com/datasets/6m7p-7yhq70029)
[5](https://redivis.com/datasets/53gc-8rhx41kgt)
[6](https://arxiv.org/html/2307.02028v3)
[7](https://proceedings.neurips.cc/paper_files/paper/2023/file/d42db1f74df54cb992b3956eb7f15a6f-Supplemental-Datasets_and_Benchmarks.pdf)
[8](https://stanfordaimi.azurewebsites.net/datasets/54c5d2a1-ef39-489e-b5f8-8f9e27e9750b)
[9](https://redivis.com/ShahLab/datasets)
[10](https://ehrshot.stanford.edu)
[11](https://shahlab.stanford.edu/doku.php?id=ehrshot)
[12](https://www.gosfield.com/images/PDF/Shay.JMPM.Your_EHR_License_Agmt.July-Aug_2014.pdf)
[13](https://neurips.cc/virtual/2023/poster/73656)
