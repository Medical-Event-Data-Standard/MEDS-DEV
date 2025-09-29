# CEHR-XGPT OMOP

This repository contains a CEHR-XGPT model customized for the **OMOP** dataset.
It is tailored to OMOP because the data pipeline includes [logic](https://github.com/cumc-dbmi/cehrbert/blob/main/src/cehrbert/data_generators/hf_data_generator/meds_to_cehrbert_conversion_rules/meds_to_cehrbert_omop.py) specific to this source, e.g. extracting and structuring visits with clear boundaries.
