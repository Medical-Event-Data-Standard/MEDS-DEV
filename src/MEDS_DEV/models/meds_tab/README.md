# MEDS-Tab Model

MEDS-Tab is a tool for tabularizing and modeling complex medical time-series data. It works by:

- Leveraging sparse representations during tabularization
- Utilizing parallelism over shards
- Computing aggregations over various time windows and codes

This approach significantly reduces the computation required to generate high-quality tree-based baseline models for any supervised learning task, while leveraging as many features as possible.

## Feature Generation

MEDS-Tab generates features by computing the cross product of three elements:

1. A MEDS `code`
2. User-defined time windows (e.g., 1 day, 1 year, full patient history)
3. The following aggregation functions for the subset of observations that fall within the time window:

- `code/count`: Number of times a `code` was observed
- `code/recency`: 1 / (1 + days since the last observation of a `code`), over the full history only
- `value/count`: Number of times a `code` had a `numeric_value`
- `value/sum`: Sum of `numeric_value` for a `code`
- `value/sum_sqd`: Sum of squared `numeric_value` for a `code`
- `value/min`: Minimum `numeric_value` for a `code`
- `value/max`: Maximum `numeric_value` for a `code`
- `static/present`: Binary indicator for presence of a `code` with null `time`
- `static/mean`: Mean `numeric_value` of a `code` with null `time`

## Models

Both models pin `meds-tab==0.5.1` and train `medsboost`, MEDS-Tab's gradient-boosted trees for wide, sparse
tabularized data.

| Model                      | Codes                             | Windows                    | Aggregations                                                                          | Training                           |
| -------------------------- | --------------------------------- | -------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------- |
| [`meds_tab/tiny`](tiny/)   | the 100 most frequent             | 7d, 30d                    | `code/count`, `value/sum`                                                             | 20-trial hyperparameter sweep      |
| [`meds_tab/large`](large/) | every code seen at least 10 times | 2h, 12h, 1d, 7d, 30d, full | `static/present`, `code/count`, `code/recency`, `value/sum`, `value/min`, `value/max` | one model, default hyperparameters |

Both use version 2 of the `model.yaml` schema, with four steps:

1. `describe` (run once per dataset and shared by every task): the code frequencies over the training split;
2. `tabularize` (per task): the features at the task's prediction times;
3. `train` (per task): the `medsboost` model;
4. `predict` (per task): the model's predictions for the requested split.

## Citation

If you use MEDS-Tab in your research, please cite:

```bibtex
@misc{oufattole2024medstabautomatedtabularizationbaseline,
      title={MEDS-Tab: Automated tabularization and baseline methods for MEDS datasets},
      author={Nassim Oufattole and Teya Bergamaschi and Aleksia Kolo and Hyewon Jeong and Hanna Gaggin and Collin M. Stultz and Matthew B. A. McDermott},
      year={2024},
      eprint={2411.00200},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2411.00200},
}
```
