# Northwestern ICU (NWICU) database

Northwestern Medicine (NM) is a network of twelve hospitals located in Chicago and the surrounding area. NM originally used a variety of electronic medical record (EMR) systems across the network, but in 2018 migrated all the hospitals to the same EMR platform, Epic. As an essential element of routine medical care, the EMR collects data on patients, admissions, diagnoses, patient status, procedures, medications, and all the other aspects of patient care.

To make EMR data available for research and quality assurance, the EMR system feeds selected data into a relational Enterprise Data Warehouse (NM EDW). The NM EDW was the source for all data supplied by NM. In order to protect patient privacy, the EDW is accessible only to the technical personnel who maintain it, database analysts affiliated with NM, and selected researchers with CITI certification in human-subjects research working on IRB-approved research studies. Raw data extracted from the EDW is stored on encrypted file servers protected by firewalls and accessible only to authorized NM and Northwestern University (NU) personnel.

NM actively pursues the use of the valuable trove of EMR data for research purposes. Recent advances in machine learning and predictive modeling, for example, have been the focus of numerous projects between Northwestern Medicine, the Feinberg School of Medicine, and other departments within Northwestern University. In general, more data means better and more accurate results, and data from any single medical center has inherent limits. To expand these limits and realize greater benefits from collected data, NM has previously joined cooperative organizations including the Center for Health Information Partnerships (CHIP) [1], the CAPriCORN [2] network of 32 hospitals, and the All of Us research program (previously known as the Precision Medicine Initiative).

By building the Northwestern ICU database, NM expands the collaborative network to provide an even broader and geographically diverse resource for researchers, particularly in the context of understanding and combating the COVID-19 pandemic. Furthermore, the adoption of standard terminologies for data coding enhances data interoperability, facilitating seamless data exchange and collaboration among healthcare institutions and researchers. While there are already several public ICU datasets available for research, including HIRID [4] and the Salzburg database, [5] these do not follow the MIMIC structure.
(source: https://physionet.org/content/nwicu-northwestern-icu/0.1.0/)

## Access Requirements

Taken from [PhysioNet](https://physionet.org/content/nwicu-northwestern-icu/0.1.0/):

- **Access Policy**: Complete the credentialed data access requirements on PhysioNet[1]
- **License (for files)**: PhysioNet Credentialed Health Data License Version 1.5.0[1]
- **Data Use Agreement**: Agreement requires verified institutional affiliation and commitment to use data solely for lawful scientific research[1]
- **Required training**: Valid CITI training certification in human research subject protection and HIPAA regulations[1]
- **License Term**: 3 years from account creation date[1]
- **Code Sharing**: Agreement to contribute code associated with publications to open research repository[1]

## Supported Tasks

NWICU includes several classification tasks organized into categories such as:[1]

**Operational Outcomes:**

- `tasks/mortality/long_length_of_stay.yaml`
- `tasks/readmission/30_day_readmission.yaml`
- `tasks/transfer/icu_transfer.yaml`

## MEDS-transformation

The NWICU ETL is found at https://github.com/rvandewater/NWICU_MEDS.

## Sources

1. [NWICU Official Website](https://physionet.org/content/nwicu-northwestern-icu/0.1.0/)

## Disclaimer

Please refer to the data owners and the most up-to-date information when using this dataset in your research. The NWICU dataset has not been reviewed or approved by the Food and Drug Administration and is for non-clinical, research and education use only.[1]
