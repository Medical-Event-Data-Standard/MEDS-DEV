# INSPIRE: a publicly available research dataset for perioperative medicine

## Description

The INSPIRE dataset is a publicly available research dataset in perioperative medicine, which includes approximately 130,000 cases (50% of all surgical cases) who underwent anesthesia for surgery at an academic institution in South Korea between 2011 and 2020. This comprehensive dataset includes patient characteristics such as age, sex, American Society of Anesthesiologists physical status classification, diagnosis, surgical procedure code, department, and type of anesthesia. It also includes vital signs in the operating theatre, general wards, and intensive care units (ICUs), laboratory results from six months before admission to six months after discharge, and medication during hospitalization. Complications include total hospital and ICU length of stay and in-hospital death.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/inspire/1.3/):

- **Access Policy**: Complete the credentialed data access requirements on PhysioNet[1]
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0[1]
- **Data Use Agreement**: Agreement requires verified institutional affiliation and commitment to use data solely for lawful scientific research[1]
- **Required training**: Valid CITI training certification in human research subject protection and HIPAA regulations[1]
- **License Term**: 3 years from account creation date[1]
- **Code Sharing**: Agreement to contribute code associated with publications to open research repository[1]

## Supported Tasks

INSPIRE includes several classification tasks organized into categories such as:[1]

**Operational Outcomes:**

- `tasks/mortality/long_length_of_stay.yaml`
- `tasks/readmission/30_day_readmission.yaml`
- `tasks/transfer/icu_transfer.yaml`

## MEDS-transformation

The INSPIRE ETL is found at https://github.com/rvandewater/INSPIRE_MEDS.

## Sources

1. [INSPIRE Physionet Website](https://physionet.org/content/inspire/1.3/)

## Disclaimer

Please refer to the data owners and the most up-to-date information when using this dataset in your research. The INSPIRE dataset has not been reviewed or approved by the Food and Drug Administration and is for non-clinical, research and education use only.[1]
