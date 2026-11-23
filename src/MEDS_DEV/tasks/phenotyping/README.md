# Phenotyping

This folder contains retrospective tasks: was a diagnosis recorded during the episode that just ended? They follow the
phenotyping tasks of the ICU benchmarks. The label lies before the prediction time, so a model must not see the
diagnosis codes of the episode.

## Excluding the label from the inputs (audit, Nov 2026)

With the stay's diagnosis codes left in the features, every phenotyping task scored AUROC 0.997-1.000 on every
dataset (MEDS-Tab features with MEDSBoost). Removing them gave 0.91-0.99, carried by the clinical signal: BNP and diuretics for
heart failure, lactate, cultures and antibiotics for sepsis, creatinine for acute kidney failure. What to remove:

- `DIAGNOSIS//` codes (`ED_DIAGNOSIS//` on MC-MED).
- MIMIC-IV `DRG//` billing groups: they are assigned at discharge from the stay's diagnoses (APR-DRG 720 is
    septicemia and was the second feature without this exclusion).
- eICU `ADMISSION_DIAGNOSIS//` (the APACHE admission diagnosis), a diagnosis field outside `DIAGNOSIS//`.

Past-history fields (eICU `PAST_HISTORY//`, MC-MED `PMH//`) record earlier disease and can stay, but for a chronic
phenotype such as heart failure they make the label largely known before the stay.
