# eICU Collaborative Research Database

## Description

The eICU Collaborative Research Database is a multi-center database comprising de-identified health data associated with over 200,000 admissions to ICUs across the United States between 2014-2015. The database includes vital sign measurements, care plan documentation, severity of illness measures, diagnosis information, and treatment information. Data is collected through the Philips eICU program, a critical care telehealth program that delivers information to caregivers at the bedside.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/eicu-crd/2.0/):

- **Access Policy**: Complete the credentialed data access requirements on PhysioNet[2]
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0[2]
- **Data Use Agreement**: Agreement requires verified institutional affiliation and commitment to use data solely for lawful scientific research[2]
- **Required training**: Valid CITI training certification in human research subject protection and HIPAA regulations[2]
- **Code Sharing**: Agreement to contribute code associated with publications to open research repository[2]

## Supported Tasks

## MEDS transformation

The [`eICU_MEDS`](https://github.com/Medical-Event-Data-Standard/eICU_MEDS) ETL downloads the original eICU-CRD data from PhysioNet and transforms it into the Medical Event Data Standard (MEDS).

MEDS-DEV pins `eICU-MEDS==0.4.0`, which registers the `eICU` spec for MEDS-Extract's `meds-extract-run`;
`build_demo` passes `dataset_key=demo`, which builds the open demo instead of the full release. The
`MEDS_extract-eICU` runner of releases up to 0.2.0 is gone. Since 0.1.0 the ETL renamed medication orders
(`MEDICATION//START//<drug>` and `MEDICATION//END//<drug>`), made `hadm_id` the hospital stay (the hospital
moved to `hospital_id`) and strips lab units of surrounding whitespace, as listed under "Breaking changes"
in its README. The predicates use none of the renamed codes, and every predicate code has events in a
full 0.4.0 build.

## Sources

1. [eICU PhysioNet Repository](https://physionet.org/content/eicu-crd/2.0/)
2. [PhysioNet Credentialed Access](https://physionet.org/content/eicu-crd/view-license/2.0/)
