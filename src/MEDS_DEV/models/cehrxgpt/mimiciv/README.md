# CEHR-XGPT MIMIC-IV

This repository contains a CEHR-XGPT model customized for the **MIMIC-IV** dataset.
It is tailored to MIMIC-IV because the data pipeline includes [logic](https://github.com/cumc-dbmi/cehrbert/blob/main/src/cehrbert/data_generators/hf_data_generator/meds_to_cehrbert_conversion_rules/meds_to_cehrbert_micmic4.py) specific to this source, including:

- Extracting and structuring visits with clear boundaries.
- Parsing numeric values stored within text fields for proper representation.
