# FEMR Count Baseline

This is the count-featurization baseline of [FEMR](https://github.com/som-shahlab/femr), following its
tutorial "Count Featurization And Modeling". The featurization is FEMR's own code, called unchanged; the
script in this directory only connects it to MEDS-DEV.

## Model

- **Features:** `femr.featurizers.AgeFeaturizer` (the age at the prediction time, not normalized) and
    `femr.featurizers.CountFeaturizer` with `string_value_combination=True`: for each subject, the number of
    times each code occurred up to (and including) the prediction time, plus one column per pair of a code
    and a text value seen more than once in training.
- **Classifier:** `xgboost.XGBClassifier()` with the library's default hyperparameters, as in the tutorial.
    A prediction is positive when its probability is above 0.5.

It uses the `supervised` profile:

1. `preprocess_data` (run once per dataset and shared by every task): converts the MEDS dataset to a
    [`meds_reader`](https://github.com/som-shahlab/meds_reader) database, FEMR's input format;
2. `train_supervised` (per task): fits the featurizers and the classifier on the labels of the train split;
3. `predict_supervised` (per task): featurizes the labels of the requested split and scores them.

## Differences from the tutorial

- The featurizers (the code vocabulary and the text value pairs) are fitted on the subjects of the train
    split only. The tutorial fits them on every labelled subject, including its test subjects.
- The splits are those of the dataset, not FEMR's hash split. The tuning split is not used: the tutorial
    selects no hyperparameters.
- Of the tutorial's two classifiers, only XGBoost is used (not the logistic regression). XGBoost is pinned
    (`xgboost==3.2.0`) and seeded.

## Known limitations

- Every predicted subject needs a `MEDS_BIRTH` event: FEMR's age featurizer fails without one.
- With the tutorial's settings, events that carry a numeric value are not counted, and events that carry a
    text value are only counted as (code, text value) pairs.
- FEMR is installed from a pinned commit of its repository, which is not in a PyPI release. It requires
    `meds==0.3.3` and `numpy<2`, in the model's own environment.
