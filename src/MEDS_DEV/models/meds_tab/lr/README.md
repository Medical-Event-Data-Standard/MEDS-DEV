# MEDS-Tab Logistic Regression Model

This model fits a logistic regression on the features of [`meds_tab/large`](../large/), using the MEDS-Tab
library (`meds-tab==0.5.1`):

- `meds-tab-tabularize` with MEDS-Tab's defaults: every code seen at least 10 times in the training split, the
    default time windows (2 hours, 12 hours, 1 day, 7 days, 30 days, and the full history) and aggregations
    (`static/present`, `code/count`, `code/recency`, `value/sum`, `value/min`, `value/max`);
- `meds-tab-model model_launcher=logistic_regression`, which fits a single scikit-learn `LogisticRegression`
    (l2 penalty, `C=1`, `lbfgs`), without a hyperparameter sweep.

Compared with MEDS-Tab's `logistic_regression` launcher, one setting is changed: `max_iter` is 1000 instead of
100\. MEDS-Tab does not scale the features, so the solver works on raw counts and sums and usually stops at
100 iterations before it has converged. The fit is also held to one BLAS thread.

MEDS-Tab stores the predictions of its tree models only, so `predict.py` scores the requested split with the
fitted model.

## Known limitations

- The features are not scaled. A logistic regression is sensitive to the scale of its columns (unlike the
    trees of `meds_tab/large`), so very large numeric values can dominate the fit.
- Nothing is tuned: the regularization strength is MEDS-Tab's default, not selected on the tuning split.
