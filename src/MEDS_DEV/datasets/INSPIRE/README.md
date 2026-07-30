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

## Sources

1. [INSPIRE PhysioNet Website](https://physionet.org/content/inspire/1.4.2/)
2. [Korea Credentialed Health Data License 1.0.0](https://physionet.org/content/inspire/view-license/1.4.2/)
