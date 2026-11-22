# INSPIRE: a publicly available research dataset for perioperative medicine

## Description

The INSPIRE dataset is a publicly available research dataset in perioperative medicine, which includes approximately 130,000 cases (50% of all surgical cases) who underwent anesthesia for surgery at an academic institution in South Korea between 2011 and 2020. This comprehensive dataset includes patient characteristics such as age, sex, American Society of Anesthesiologists physical status classification, diagnosis, surgical procedure code, department, and type of anesthesia. It also includes vital signs in the operating theatre, general wards, and intensive care units (ICUs), laboratory results from six months before admission to six months after discharge, and medication during hospitalization. Complications include total hospital and ICU length of stay and in-hospital death.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/inspire/1.4.2/):

- **Access Policy**: Only credentialed users who sign the data use agreement can access the files.[1]
- **License**: Korea Credentialed Health Data License 1.0.0.[1]
- **Data Use Agreement**: Korea Credentialed Health Data Agreement 1.0.0; the data may be used for research purposes only.[1,2]
- **Required training**: CITI Data or Specimens Only Research.[1]
- **Agreement term**: Five years, automatically extended unless notice is given.[2]

## Supported Tasks

## MEDS transformation

The [`INSPIRE_MEDS`](https://github.com/rvandewater/INSPIRE_MEDS) ETL transforms the original INSPIRE data from PhysioNet into the Medical Event Data Standard (MEDS).

MEDS-DEV pins `INSPIRE-MEDS==1.2.0`, which registers the `INSPIRE` spec for MEDS-Extract's
`meds-extract-run`; `MEDS_extract-INSPIRE`, the complete build up to 1.0.0, is deprecated. Since 1.0.0 the
ETL renamed diagnoses (`ICD//<edition>//<code>`) and operation and anaesthesia intervals
(`OPERATION//START`, `OPERATION//END`, `ANESTHESIA//START`, `ANESTHESIA//END`), strips lab and vital units of
surrounding whitespace and adds `hadm_id` and `operation_id` columns, as listed under "Breaking changes" in
its README. The predicates use none of the renamed codes, and every predicate code has events in a full
1.2.0 build.

## Known issues (audit, Nov 2026)

- Diagnoses keep 3-character ICD-10 codes, so personal-history codes (Z85) cannot be split by cancer site and
  diabetes is often coded E14 (unspecified diabetes, now included in the diabetes predicates).
- The hospital discharge is sometimes stamped before the ICU discharge, and ICU-anchored mortality scores about 0.98
  against 0.90-0.93 on eight other datasets, with no single dominant feature: worth checking the discharge and death
  timestamps.
- As a surgical registry, most ICU transfers, short stays and many readmissions follow the surgical plan (planned
  post-operative ICU stays, second-eye cataract surgery within 30 days).

## Sources

1. [INSPIRE PhysioNet Website](https://physionet.org/content/inspire/1.4.2/)
2. [Korea Credentialed Health Data License 1.0.0](https://physionet.org/content/inspire/view-license/1.4.2/)
