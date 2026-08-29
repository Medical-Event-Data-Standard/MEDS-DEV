# MEDS-EIC-AR

[MEDS-EIC-AR](https://github.com/mmcdermott/MEDS_EIC_AR) — "Everything is Code" autoregressive
generative model for MEDS data. Tokenizes a MEDS dataset, tensorizes it for
[`meds-torch-data`](https://github.com/mmcdermott/meds-torch-data), pretrains a transformer LM
via PyTorch Lightning, and (in the zero-shot setting) generates future patient trajectories that
can be resolved into task predictions.

The whole pipeline is **dataset-agnostic** — nothing here is wired per-dataset; the same commands
run against any MEDS dataset.

## Capacity variants

Registered as four sibling variants, each selecting an upstream `lightning_module=<size>` preset
(matching the `meds_tab/tiny` capacity-variant pattern):

| Variant                         | Layers | Heads × dim | Hidden size |
| ------------------------------- | ------ | ----------- | ----------- |
| [`meds_eic_ar/micro`](micro/)   | 4      | 4 × 64      | 256         |
| [`meds_eic_ar/small`](small/)   | 8      | 8 × 64      | 512         |
| [`meds_eic_ar/medium`](medium/) | 12     | 12 × 64     | 768         |
| [`meds_eic_ar/large`](large/)   | 24     | 16 × 64     | 1024        |

## `unsupervised: train`

Fully wired. Two upstream steps:

1. `MEICAR_process_data` — tokenize + tensorize the MEDS dataset.
2. `MEICAR_pretrain` — autoregressive pre-training.

In `demo=True` mode both steps use the upstream demo configs (`do_demo=True`,
`--config-name=_demo_pretrain`), which lower filtering thresholds and training cost so the demo
data survives and the run finishes quickly. In full mode, `MEICAR_pretrain lightning_module=<size>`
selects the variant's capacity preset. (Demo mode currently runs the upstream demo capacity for
all four variants — a CI-cost tradeoff; if we want each variant to exercise its own architecture
under demo we can override `lightning_module/model` on top of the demo config.)

## `supervised: predict` — zero-shot, partially wired

Zero-shot inference is a two-step process upstream:

1. **Generate trajectories** — `MEICAR_generate_trajectories` rolls future patient timelines
    forward from each task sample's prediction time. **This step is wired up** in each variant's
    `supervised: predict` command; it consumes the pretrained model + tensorized cohort from the
    `unsupervised: train` stage and the task labels dir, and writes per-sample trajectory parquets.

2. **Resolve trajectories into predictions** — turn the generated futures into a
    `predictions.parquet` (empirical event probability per task sample) in
    [`meds-evaluation`](https://github.com/Medical-Event-Data-Standard/meds_evaluation) format.
    **This step is not yet wired**, blocked on two gaps:

    - **MEDS-DEV gap:** [`meds-trajectory-evaluation`](https://github.com/mmcdermott/MEDS_trajectory_evaluation)'s
        `ZSACES_label` CLI needs the ACES task criteria + dataset predicates files. MEDS-DEV does
        not currently pass those to model `supervised` commands — the only template variables
        available are `dataset_dir`, `labels_dir`, `model_initialization_dir`, `output_dir`,
        `model_dir`, `split`, and `demo`. Tracked in
        [#314](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/issues/314).
    - **Upstream gap:** even with `ZSACES_label` runnable, it emits *per-trajectory* boolean
        labels (`valid` / `determinable` / `label`), not an aggregated empirical-probability
        `predictions.parquet`. There is no CLI to aggregate across the N sampled trajectories per
        task sample and emit a `meds-evaluation`-compatible predictions file. Tracked upstream in
        [mmcdermott/MEDS_trajectory_evaluation#42](https://github.com/mmcdermott/MEDS_trajectory_evaluation/issues/42).

Once both land, each variant's `supervised: predict` gains the `ZSACES_label` + aggregation steps
and produces `{output_dir}/predictions.parquet`. Until then the supervised lane stops after
trajectory generation, so the model-lane integration test will not produce a packaged result.

## Optional dependencies

The upstream package ships extras for `[wandb]` and `[mlflow]`, plus flash-attn (installed
separately). MEDS-DEV installs the base package only; install extras into the model's venv after
MEDS-DEV provisions it if you want them during a benchmark run.
