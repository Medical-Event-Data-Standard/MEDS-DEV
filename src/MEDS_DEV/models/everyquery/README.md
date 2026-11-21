# EveryQuery (zero-shot)

[EveryQuery](https://github.com/payalchandak/EveryQuery) is a model that answers questions about a
patient's future from the record so far: "given the record up to the prediction time, does code *c* occur in
window *W*, given these answers about earlier windows?". It is pretrained self-supervised, on the dataset
alone. Here it is used **zero-shot**: it is never trained on a task's labels.

The model is run through the
[`meds-algorithm-everyquery`](https://pypi.org/project/meds-algorithm-everyquery/) package, which was
generated from the [MEDS algorithm template](https://github.com/McDermottHealthAI/MEDS_algorithm_template).

## How a task is answered

A task is given to the model as its ACES criteria file and the dataset's predicates, not as labels:

1. the criteria are translated into EveryQuery queries: the label becomes one window, and criteria that
    must hold become conditioning queries with forced answers;
2. EveryQuery scores the queries for each prediction time;
3. the scores are decoded into one probability per prediction time.

The task that is answered is not always exactly the task that was asked. Every difference (for example a
value threshold that falls inside a value bin, or a criterion that cannot be expressed) is recorded in
`relaxations.yaml`, next to the predictions, together with the quantity that was decoded. The intermediate
plan, query grid and raw scores are kept in `bundle/`.

## Steps

It uses the `zero_shot_direct` profile:

1. `preprocess_data` (run once per dataset and shared by every task): tensorizes the dataset and builds the
    code ontology. The vocabulary and the value bins are fitted on the train split;
2. `pretrain` (run once per dataset and shared by every task): samples query sequences on the train and
    tuning splits and trains the model, without any task or label;
3. `predict_zero_shot_direct` (per task): translates the task, scores it and decodes the predictions.

Running several tasks with the same `output_dir` therefore pretrains the model once.

## Requirements and settings

- The package requires **Python 3.12**; `model.yaml` sets `python: "3.12"`, so the model's environment is
    built with that version whatever interpreter MEDS-DEV runs on.
- A full run uses EveryQuery's own defaults: codes seen in at least 1000 subjects, subjects with at least 10
    events, and EveryQuery's production training configuration. Pretraining needs a GPU at that scale.
- A demo run (`demo=True`) uses [`demo_config.yaml`](demo_config.yaml): a small model trained for 5 epochs
    on CPU, with the code and subject filters lowered for demo-sized datasets. Its predictions only show
    that the pipeline runs.
- A demo run also limits preprocessing to one polars thread (`POLARS_MAX_THREADS=1`). EveryQuery's
    preprocessing is memory-hungry with several threads: on the eICU demo (54 MB of data) it peaks at about
    15 GB with two or more threads, and at about 5 GB with one. A full run does not set this limit, so plan
    its memory accordingly, or set `POLARS_MAX_THREADS` yourself.

## Known limitations

- Only the `tuning` and `held_out` splits can be predicted: the `train` split is the pretraining data.
- Codes rarer than the code filter are not in the vocabulary, so a task whose label matches no vocabulary
    code cannot be posed and fails.
- Prediction times with no earlier event cannot be scored; they get the mean of the scored probabilities,
    and their number is recorded in `coverage.json`.
- A value threshold that falls inside a value bin loses that bin.
