# MEDS-Tab Large Model

This model runs the MEDS-Tab library (`meds-tab==0.5.1`) with its defaults:

- `meds-tab-tabularize` over every code seen at least 10 times in the training split, with the default time
    windows (2 hours, 12 hours, 1 day, 7 days, 30 days, and the full history) and aggregations
    (`static/present`, `code/count`, `code/recency`, `value/sum`, `value/min`, `value/max`);
- `meds-tab-model`, which trains a single `medsboost` classifier (MEDS-Tab's gradient-boosted trees) with its
    default hyperparameters, without a hyperparameter sweep.

See [`meds_tab/tiny`](../tiny/) for a cheaper variant with fewer codes, windows and aggregations.
