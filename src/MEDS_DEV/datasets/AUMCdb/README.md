# AUMCdb

## Description

The first freely accessible intensive care database from within the European Union containing de-identified health data related to tens of thousands of European intensive care unit admissions, including demographics, vital signs, laboratory tests and medications.

## Access Requirements

Taken from [official website](https://amsterdammedicaldatascience.nl/amsterdamumcdb/#requesting-access):

- **Access Policy**: Fill out and sign the combined Access and End User License form.
- **License (for files)**: Specify the license under which the dataset files are distributed.
- **Data Use Agreement**: Agreement found [here](https://amsterdammedicaldatascience.nl/content/uploads/sites/2/2022/12/arfeula_v1.6.pdf).
- **Required training**: Valid training courses include the Data or Specimens Only Research (DSOR) course from CITI, the Basic Course for Clinical Investigators (BROK) from NFU or an equivalent course. The DSOR course may be taken free of charge and is also needed to gain access to the MIMIC and eICU intensive care databases from the USA.

## Supported Tasks

- `tasks/mortality/in_icu/first_24h.yaml`

## MEDS-transformation

[`AUMCdb-MEDS`](https://github.com/prockenschaub/AUMCdb_MEDS) 0.3.0, pinned in `requirements.txt`, registers
the `AUMCdb` spec for MEDS-Extract's `meds-extract-run`, which downloads the DataVerse archives into
`raw_input_dir`, builds the MEDS dataset and, as a last step, enriches `metadata/codes.parquet` with suMEDS.
The download needs a DANS DataVerse API key in `AUMCDB_API_KEY`, and the package requires Python
`>=3.11.4,<3.14`. The `MEDS_extract-AUMCdb` command the previous pin used is gone. The ETL's README lists its
code and column changes under "Breaking changes"; 0.3.0 adds an `icustay_id` column and strips units in
codes of surrounding whitespace.

Creatinine is `MEASURE//Kreatinine (bloed)//µmol/l`, so the elevated-creatinine threshold of 1.3 mg/dL is
115 µmol/l. Earlier versions of `predicates.yaml` spelled the unit with a broken character and also listed
a `MEASURE//Kreatinine//µmol/l` code the release does not have; neither matched any event. Every predicate
code has events in a full 0.3.0 build.

## Sources

1. [AUMCdb dataset](https://amsterdammedicaldatascience.nl/amsterdamumcdb/)
2. [AUMCdb Research Paper](https://journals.lww.com/ccmjournal/fulltext/2021/06000/sharing_icu_patient_data_responsibly_under_the.16.aspx)
3. [AUMCdb Data Use Agreement](https://amsterdammedicaldatascience.nl/content/uploads/sites/2/2022/12/arfeula_v1.6.pdf)
4. [Data Repository](https://easy.dans.knaw.nl/ui/home)
5. [Code Repository](https://github.com/AmsterdamUMC/AmsterdamUMCdb)

## Disclaimer

Please refer to the data owners and the most up-to-date information when using this dataset in your research.
