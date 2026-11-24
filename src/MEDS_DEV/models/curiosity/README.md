# Curiosity (zero-shot, generated futures)

[Curiosity](https://arxiv.org/abs/2611.15710) is Epic's generative medical event model: a decoder-only transformer
(Qwen2) pretrained to predict a patient's next medical event. It answers a task by **simulating futures**: it samples
many continuations of the patient's record from the prediction time, and the prediction is the fraction of futures in
which the outcome happens. It is never trained on a task's labels.

These models are run through the
[`meds-algorithm-curiosity`](https://pypi.org/project/meds-algorithm-curiosity/) package, a paper-only port of
Curiosity-0826 (arXiv 2611.15710, building on Curiosity-0226, arXiv 2508.12104) generated from the
[MEDS algorithm template](https://github.com/McDermottHealthAI/MEDS_algorithm_template). No code, weights or data
were released with the papers.

## Models

| Model                         | Size preset | Shape (layers × width, heads) | Parameters (at 0226's 7,105-token vocabulary) |
| ----------------------------- | ----------- | ----------------------------- | --------------------------------------------- |
| [`curiosity/small`](small/)   | `small`     | 6 × 768, 12                   | 62M (0226 Curiosity-S)                        |
| [`curiosity/medium`](medium/) | `medium`    | 12 × 768, 12                  | 119M (0226 Curiosity-M)                       |

The package also has `large` (16 × 2048, 1.09B; 0226 Curiosity-L) and `xlarge` (40 × 2560, ~4.2B; Curiosity-0826-4B)
presets. They are not registered here: public MEDS datasets are far below the data those sizes were trained on.

## How a task is answered

It uses the `zero_shot_materialized` profile:

1. `preprocess_data` (once per dataset, shared by every task): tokenizes every event. The vocabulary and value
    buckets are fitted on the train split. The prompt for a prediction time is built only from what is recorded at or
    before it.
2. `pretrain` (once per dataset, shared by every task): next-event pretraining on the train split, then the paper's
    extended-context stage (8,192 then 16,384 tokens). No task or label is used.
3. `infer_trajectories` (per task): samples futures (60 of up to 4,000 tokens by default) from each held-out
    prediction time. It reads the task's keys, not its labels.
4. `predict_zero_shot_materialized` (per task): evaluates the task's ACES criteria on history plus each future. The
    probability is the share of positive futures among those that resolve the task; a key with none gets 0.5 and is
    listed in `unresolved_keys.arrow`. The approximations are recorded in `relaxations.yaml`.

## Vocabulary

The tokenization is dataset-agnostic, so any MEDS dataset runs without configuration. This is an adaptation: the
papers tokenize fixed event types (ICD diagnoses split into sub-tokens, labs, clinical vital bins, ATC medications)
and drop other codes.

- Every code is one whole-code token, with no code-hierarchy split. Codes rarer than a frequency threshold become an
    unknown token, as in the papers.
- A code with enough numeric values in the training split is followed by one of 30 value buckets (the papers' lab
    buckets), a code with text values by a result token, and a row with route, dose or frequency columns by attribute
    tokens.
- The latest value of each numeric code in each 6-hour window is kept (the papers do this for vitals).
- `MEDS_BIRTH` gives the age at the start of the timeline; `MEDS_DEATH` ends the record.

So any task whose codes occur in the training split can be answered.

## Requirements and settings

- The package requires **Python 3.12** (`python: "3.12"` in `model.yaml`).
- A full run uses the size preset and the package defaults. Pretraining and sampling need a GPU at that scale; sampling
    costs about 60 × 4,000 generated tokens per prediction time.
- A demo run (`demo=True`) uses `demo_config.yaml`: a two-layer model trained for 5 epochs on CPU, with 8 futures of
    up to 256 tokens. Its predictions only show that the pipeline runs.

## Known limitations

- Futures are generated for the `held_out` split only (the `infer_trajectories` step does not receive `{split}`), so
    only `held_out` can be predicted.
- A task whose codes never occur in the training split, or are rarer than the threshold, cannot be generated,
    and is rejected before any work.
- Generated values are sampled within a value bucket, so a threshold that falls inside a bucket is evaluated on
    sampled values.
