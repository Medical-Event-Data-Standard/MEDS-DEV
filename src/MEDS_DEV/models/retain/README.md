# RETAIN

RETAIN ([Choi et al., NeurIPS 2016](https://proceedings.neurips.cc/paper/2016/hash/231141b34c82aa95e48810a9d1b33a79-Abstract.html))
is a reverse-time attention model: it reads a subject's visits from the most recent to the oldest, and
predicts a binary outcome from a weighted sum of the codes of each visit.

This model runs the [`meds-algorithm-retain`](https://pypi.org/project/meds-algorithm-retain/) package
(pinned to `0.1.0`, [source](https://github.com/florian6973/meds-algorithm-retain)), a PyTorch
reimplementation of the official Theano code
([`mp2893/retain`](https://github.com/mp2893/retain)) built with the
[MEDS algorithm template](https://github.com/McDermottHealthAI/MEDS_algorithm_template). This directory
holds no code: `model.yaml` calls the package's `retain-meds` command.

## Model

- **Input:** the codes of each subject up to (and including) the prediction time. A visit is the set of
    codes recorded in one calendar day. Numeric values, events without a time, `MEDS_BIRTH` and `MEDS_DEATH`
    are not used.
- **Vocabulary:** every code of the train split. Codes that only occur in other splits are dropped.
- **Architecture and training:** the official defaults (embedding and both attention GRUs of size 128,
    batch size 100, 10 epochs, Adadelta, dropout 0.5, L2 0.001). The epoch with the best AUROC on the tuning
    split is kept.
- **Prediction:** every requested key is scored. A key without any history gets the model's learned
    intercept. A prediction is positive when its probability is above 0.5.

It uses the `supervised` profile:

1. `preprocess_data` (run once per dataset and shared by every task): fits the code vocabulary on the train
    split and tokenizes the events;
2. `train_supervised` (per task): fits the model on the labels of the train split, and selects the epoch on
    the labels of the tuning split;
3. `predict_supervised` (per task): scores the labels of the requested split.

## Differences from the official implementation

- The official code starts from visits that are already built (one per hospital admission in its MIMIC-III
    example). Here a visit is one calendar day of codes, which needs no dataset-specific definition of an
    admission.
- Codes are not grouped (the official example truncates ICD-9 codes to 3 digits): every distinct MEDS code
    is a vocabulary entry.
- The dataset's own splits are used, not a split made by the official code.

## Known limitations

- The labels directory must name its splits in its file paths (`train/...`, `tuning/...`, `held_out/...`),
    as `meds-dev-task` writes them.
- It trains on a GPU when one is available, and otherwise on the CPU, where the fit of a full dataset is slow.
- Predictions on a GPU are not bit-for-bit reproducible across machines.

## Citation

```bibtex
@inproceedings{choi2016retain,
  title={RETAIN: An Interpretable Predictive Model for Healthcare using Reverse Time Attention Mechanism},
  author={Choi, Edward and Bahadori, Mohammad Taha and Kulas, Joshua A and Schuetz, Andy and Stewart, Walter F and Sun, Jimeng},
  booktitle={Advances in Neural Information Processing Systems},
  volume={29},
  pages={3504--3512},
  year={2016}
}
```
