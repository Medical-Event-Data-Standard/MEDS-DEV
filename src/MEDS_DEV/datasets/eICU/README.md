# eICU Collaborative Research Database

## Description

The eICU Collaborative Research Database is a multi-center database comprising de-identified health data associated with over 200,000 admissions to ICUs across the United States between 2014-2015. The database includes vital sign measurements, care plan documentation, severity of illness measures, diagnosis information, and treatment information. Data is collected through the Philips eICU program, a critical care telehealth program that delivers information to caregivers at the bedside.[1]

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/eicu-crd/2.0/):

- **Access Policy**: Complete the credentialed data access requirements on PhysioNet[2]
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0[2]
- **Data Use Agreement**: Agreement requires verified institutional affiliation and commitment to use data solely for lawful scientific research[2]
- **Required training**: Valid CITI training certification in human research subject protection and HIPAA regulations[2]
- **License Term**: 3 years from account creation date[2]
- **Code Sharing**: Agreement to contribute code associated with publications to open research repository[2]

## Supported Tasks

eICU includes several classification tasks organized into categories such as:[1]

**Operational Outcomes:**

- `tasks/mortality/long_length_of_stay.yaml`
- `tasks/readmission/30_day_readmission.yaml`
- `tasks/transfer/icu_transfer.yaml`

## MEDS-transformation

eICU is available in three formats: Original (compatible with benchmark repository), MEDS (Medical Event Data Standard), and OMOP (full OMOP table dumps). The MEDS version contains the same exact data as the Original dataset but in MEDS-compatible format.[1]

## Sources

1. [eICU Physionet Repository](https://physionet.org/content/eicu-crd/2.0/)
2. [PhysioNet Credentialed Access](https://physionet.org/content/eicu-crd/view-license/2.0/)

## Disclaimer

Please refer to the data owners and the most up-to-date information when using this dataset in your research. The eICU dataset has not been reviewed or approved by the Food and Drug Administration and is for non-clinical, research and education use only.[2]
