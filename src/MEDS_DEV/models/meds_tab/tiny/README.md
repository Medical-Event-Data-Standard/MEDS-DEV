# MEDS-Tab Tiny Model

This is a tiny model that uses the MEDS-Tab library (`meds-tab==0.5.1`) to tabularize data with
`meds-tab-tabularize` and then tunes a `medsboost` classifier (MEDS-Tab's gradient-boosted trees) over 20
trials to make predictions. Only the top 100 most prevalent codes are used, with time windows of 7 days and 30
days. Two aggregation methods are used in tabularization: counting code occurrences and summing numeric
values.
