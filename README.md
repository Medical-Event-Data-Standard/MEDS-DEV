# MEDS-DEV: Establishing Reproducibility and Comparability in Health AI

[![PyPI - Version](https://img.shields.io/pypi/v/MEDS-DEV)](https://pypi.org/project/MEDS-DEV/)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FMedical-Event-Data-Standard%2FMEDS-DEV%2Fmain%2Fpyproject.toml&logo=python&logoColor=white)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/blob/main/pyproject.toml)
[![MEDS v0.4](https://img.shields.io/badge/MEDS-0.4-blue)](https://medical-event-data-standard.github.io/)
[![Tests](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/tests.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/Medical-Event-Data-Standard/MEDS-DEV/graph/badge.svg?token=5RORKQOZF9)](https://codecov.io/gh/Medical-Event-Data-Standard/MEDS-DEV)
[![Code Quality](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/code-quality-main.yaml/badge.svg?branch=main)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/code-quality-main.yaml?query=branch%3Amain)
[![uv](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fuv%2Fmain%2Fassets%2Fbadge%2Fv0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fastral-sh%2Fruff%2Fmain%2Fassets%2Fbadge%2Fv2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Hydra](https://img.shields.io/badge/Config-Hydra_1.3-89b8cd)](https://hydra.cc/)
[![License](https://img.shields.io/github/license/Medical-Event-Data-Standard/MEDS-DEV)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/blob/main/LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/blob/main/CONTRIBUTORS.md)
[![Contributors](https://img.shields.io/github/contributors/Medical-Event-Data-Standard/MEDS-DEV)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/graphs/contributors)
[![Datasets](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FMedical-Event-Data-Standard%2FMEDS-DEV%2F_web%2Fbadges%2Fdatasets.json)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/tree/main/src/MEDS_DEV/datasets)
[![Tasks](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FMedical-Event-Data-Standard%2FMEDS-DEV%2F_web%2Fbadges%2Ftasks.json)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/tree/main/src/MEDS_DEV/tasks)
[![Models](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FMedical-Event-Data-Standard%2FMEDS-DEV%2F_web%2Fbadges%2Fmodels.json)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/tree/main/src/MEDS_DEV/models)

The MEDS Decentralized, Extensible Validation (MEDS-DEV) system is a new kind of benchmark for Health AI that
has three key differences from existing systems:

1. **Reproducibility first**: MEDS-DEV is built for the [MEDS](https://medical-event-data-standard.github.io/)
    Health AI ecosystem, and all model training recipes submitted to MEDS-DEV should, in theory, be
    transportable to any MEDS-compliant dataset. _This means you can take any of the models profiled here and
    try them on your data as baselines for your papers!_ Similarly, all task definitions are
    [ACES](https://eventstreamaces.readthedocs.io/en/latest/) task configuration files, and should be
    extractable on any compatible dataset, provided the local data owner can identify the right predicates
    needed for each given task.
2. **Decentralized Benchmarking**: MEDS-DEV is built for the real world of health data -- a world of
    fragmented, decentralized access to data where experiments over key datasets must be run by local
    collaborators with access to those datasets, not by model authors. But even though datasets are fragmented,
    MEDS-DEV shows that results, reproducible training recipes, and insights don't have to be. _This means we
    encourage you to upload new task definitions or new models that you've only profiled on a subset of
    datasets, as long as you provide the training recipes and task definitions!_ In time, we can "complete" the
    landscape of comparisons over datasets, tasks, and models, and MEDS-DEV is developing methods to produce
    generalizable insights even from decentralized results.
3. **Extensible Predictive Landscape**: Health AI isn't a field defined by one, two, or even a dozen
    prediction targets. We have myriad tasks of interest across all areas of clinical care, with tasks further
    changing over time as new diseases or health needs emerge across the world. MEDS-DEV is built to help us
    operationalize these different needs through the common, extensible repository of task definitions
    contained here. _This means you can add new tasks to MEDS-DEV, and we encourage you to do so!_ Adding new
    tasks, even with no supported datasets, gives the community an opportunity to comment, critique, and refine
    these task definitions so that we can collectively operationalize what is worth studying in Health AI.

Beyond these factors, MEDS-DEV also aims to make it easier to perform meaningful, fair comparisons across AI
systems, with standardized baselining systems that can be used on any task and dataset, a consistent
evaluation paradigm to provide a common currency for comparison, and a commitment to open science,
transparency, and reproducibility to help drive the field forward.

To see supported MEDS-DEV tasks, datasets, and models, see the links below:

1. [Tasks](src/MEDS_DEV/tasks)
2. [Datasets](src/MEDS_DEV/datasets)
3. [Models](src/MEDS_DEV/models)

Note that this repository is _not_ a place where functional code is stored. Rather, this repository stores
configuration files, training recipes, results, etc. for the MEDS-DEV benchmarking effort -- runnable code
will often come from other repositories, with operationalized instructions on how to leverage that external
code in the given entry points for those models.

To see how to use and contribute to MEDS-DEV, see the sections below!

## Installation

MEDS-DEV supports Python 3.11, 3.12, and 3.13; use Python 3.11 to run benchmarks. Dataset ETLs and models
run in virtual environments built with the same Python version as MEDS-DEV, and the end-to-end tests only
run them on 3.11. Python 3.14 is not supported yet, because `hydra-core` 1.3, which every MEDS-DEV command
uses, crashes on 3.14.

If you just want to reproduce MEDS-DEV models and tasks over public or your own, local datasets, you can
install MEDS-DEV from [PyPI](https://pypi.org/project/MEDS-DEV/) via `pip install MEDS-DEV`.

If you want to _contribute new models, tasks, or datasets_ to MEDS-DEV, you need to fork this repository,
clone your fork, and then install the repository locally in "editable" mode via `uv sync` (see
[`CONTRIBUTORS.md`](CONTRIBUTORS.md)).
This will let you prepare your PR code and run the tests to ensure your contributions are valid and
transportable across MEDS-DEV datasets and tasks.

> [!WARNING]
> MEDS-DEV supports Linux and macOS only; native Windows is not supported. MEDS-DEV runs dataset and model
> commands through `bash` in POSIX-style virtual environments, which do not work natively on Windows. On a
> Windows machine, run MEDS-DEV inside the [Windows Subsystem for Linux
> (WSL)](https://learn.microsoft.com/windows/wsl/) instead.

## Using Existing MEDS-DEV Datasets, Tasks, or Models

To reproduce a MEDS-DEV result (or transport a MEDS-DEV result to your local dataset), you will generally need
to perform the following four steps:

1. Build the target dataset in MEDS format (if it is not already built).
2. Extract the task(s) of interest from that dataset.
3. Train the model(s) of interest on the extracted task(s) and make predictions for the test set. This may
    involve both unsupervised training (a.k.a. pre-training) and supervised training (a.k.a. fine-tuning),
    depending on the model.
4. Evaluate the predictions of the model(s) over the task(s) for the given dataset.

MEDS-DEV has helper functions to help you easily perform all of these steps.

### Building a dataset

> [!NOTE]
> If your dataset is already extracted in the MEDS format, you can skip this step and assume that
> `$DATASET_DIR` points to the directory containing your MEDS-formatted dataset.

To build a supported dataset that you have access to in the MEDS format at the specified version used in
MEDS-DEV, you can use the `meds-dev-dataset` helper:

```bash
meds-dev-dataset dataset=$DATASET_NAME output_dir=$DATASET_DIR
```

where `DATASET_NAME` is the name of the dataset you want to build and `OUTPUT_DIR` is the directory where you
want to store the final, MEDS-formatted dataset.

If you have already downloaded the raw source data, point the builder at it to avoid downloading it again:

```bash
meds-dev-dataset dataset=$DATASET_NAME output_dir=$DATASET_DIR raw_input_dir=/path/to/downloaded/data
```

If the directory is empty, the ETL downloads the data into it (for datasets whose ETL can download), so it can
be reused for later builds. If `raw_input_dir` is omitted, the raw data is downloaded to a temporary directory
that is removed after the build. `do_overwrite=True` never deletes `raw_input_dir`.

> [!NOTE]
> Note that you can also specify `demo=True` to build a demo version of this dataset (if supported) for ease
> of testing the pipeline and your downstream code.

> [!NOTE]
> Note that here, `$DATASET_NAME` is the entire, slash-separated path from `src/MEDS_DEV/datasets/` to the
> directory containing the dataset's `commands.yaml` and `README.md` files. This name is a unique identifier
> for MEDS-DEV datasets so that the right task-specific predicates can be used and that it is clear what
> results were built on what dataset.

### Extracting a task

> [!NOTE]
> If your task labels are already extracted in the MEDS format, you can skip this step and assume that
> `$LABELS_DIR` points to the directory containing your MEDS-formatted task labels for the specific task of
> interest.

> [!NOTE]
> MEDS-DEV currently only supports binary classification tasks.

To extract a task from a dataset, you can use the `meds-dev-task` helper:

```bash
meds-dev-task task=$TASK_NAME dataset=$DATASET_NAME output_dir=$LABELS_DIR dataset_dir=$DATASET_DIR
```

where `$TASK_NAME` is the name of the task you want to extract, `$DATASET_NAME` is the name of the dataset you
are extracting from (this name is used to locate the right `predicates.yaml` file for the task),
`$DATASET_DIR` is the root directory for the MEDS-compliant dataset, and `$LABELS_DIR` is the directory where
you want to store the extracted task labels. The output will be a set of parquet files in the
[meds](https://github.com/Medical-Event-Data-Standard/meds) label format.

> [!WARNING]
> Right now, we don't have a good way to point to predicates files on disk that are used for datasets not yet
> configured for MEDS-DEV. File a new or up-vote any existing relevant GitHub issues for this functionality if
> it would be helpful for you! In general, we encourage that, eventually, any dataset over which MEDS-DEV
> results are reported publicly (e.g., in a publication) be added to MEDS-DEV (this does not necessitate data
> release -- merely that you include the predicate definitions used linked to a unique name, and ideally to
> the code you use to build the MEDS view of these data so others at your site can contribute in a
> reproducible way).

> [!NOTE]
> Note that here, `$TASK_NAME` is the entire, slash-separated path from `src/MEDS_DEV/tasks/` to the
> task configuration file. This name is a unique identifier for MEDS-DEV tasks.

> [!NOTE]
> Note that _it is guaranteeably true that not all tasks will be appropriate for or supported on all
> datasets._ Some tasks are only suited for certain clinical populations, which may not exist on all datasets.
> We're still figuring out the best way to operationalize this formally, but for now, please be cognizant of
> whether or not a task should be used on your dataset, and if you have ideas on this, don't hesitate to weigh
> in on [the GitHub Issue](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/issues/60) about this!

### Using a model

> [!NOTE]
> MEDS-DEV is not about (for now) assessing the generalizability of fully pre-trained models from site A to
> site B. Instead, it is about assessing the generalizability of model _training recipes_ (e.g., algorithms).
> This section reflects that by giving instructions on how you can use MEDS-DEV to train a model from scratch
> on an included or your custom dataset.

To train a model on a task, you can use the `meds-dev-model` helper. This helper is a bit more complicated
than the other helpers, because there are a few different modes in which you could use a model. Namely, you
could either: (a) train a model or (b) make predictions with a model (controlled via the `mode` parameter);
and you could additionally use a model either over (a) unsupervised (e.g., pre-training) or (b) supervised
(e.g., fine-tuning) data (controlled via the `dataset_type` parameter). Let's see each of these modes in
action with a hypothetical sequence of uses of the command to pre-train a model, then fine-tune it, then make
predictions.

```bash
# 1. Pre-train a model on unsupervised data
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR mode=train dataset_type=unsupervised output_dir=$PRETRAINED_MODEL_DIR

# 2. Fine-tune a model on supervised data
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR labels_dir=$LABELS_DIR mode=train dataset_type=supervised output_dir=$FINETUNED_MODEL_DIR model_initialization_dir=$PRETRAINED_MODEL_DIR

# 3. Make predictions with a model for the held-out set:
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR labels_dir=$LABELS_DIR mode=predict dataset_type=supervised split=held_out output_dir=$PREDICTIONS_DIR model_initialization_dir=$FINETUNED_MODEL_DIR
```

Here, `$MODEL_NAME` is the name of the model you want to train within the MEDS-DEV ecosystem. You can see that
the pre-trained model weights are passed to the fine-tuning stage via the `model_initialization_dir`
parameter, and likewise for the fine-tuned model weights to the prediction stage.

> [!NOTE]
> If you're a model creator, don't worry that you'll have to conform to this API -- this is just the API for
> model users, and internally MEDS-DEV wraps this API into whatever custom scripts and calls you need your
> model to take to train and predict. See the section below about "Contributing" for more details!

> [!NOTE]
> You can also run the full suite of supported commands for a model in the right order, chaining directories
> as needed, using the `mode=full` and `dataset_type=full` options. This will run the full sequence of
> commands in 1-3 above, and store the intermediate results in subdirectories of the output directory.

#### What `unsupervised` and `supervised` mean

The two `dataset_type`s differ in whether a stage depends on a task, not only in whether it uses labels:

| `dataset_type` | Receives `{labels_dir}`? | Depends on the task? | Typical use                                                             |
| -------------- | ------------------------ | -------------------- | ----------------------------------------------------------------------- |
| `unsupervised` | no                       | no                   | pre-training (run once per dataset, reusable by every task)             |
| `supervised`   | yes                      | yes                  | task-specific training, and prediction for a task (including zero-shot) |

A zero-shot model therefore defines `unsupervised.train` (pre-training) and `supervised.predict`, with
`supervised.train` set to `null`. It predicts in `supervised` mode because it needs the task's labels
directory (the rows to predict) and, through `{task_criteria_path}`, the task's definition.

#### Reusing one pre-trained model across several tasks

Pre-training does not depend on the task, so you can pre-train once and reuse the result for many tasks.
There are two ways to do this.

**Explicit stages.** Pre-train once, then point every task's stages at that directory:

```bash
# Pre-train once per dataset
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR mode=train dataset_type=unsupervised \
	output_dir=$RUN_DIR/pretrain

for TASK_NAME in $TASKS; do
	meds-dev-task task=$TASK_NAME dataset=$DATASET_NAME dataset_dir=$DATASET_DIR output_dir=$LABELS_ROOT/$TASK_NAME

	# Fine-tune. Zero-shot models skip this command and use $RUN_DIR/pretrain as model_initialization_dir below.
	meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR labels_dir=$LABELS_ROOT/$TASK_NAME \
		task_name=$TASK_NAME mode=train dataset_type=supervised \
		model_initialization_dir=$RUN_DIR/pretrain output_dir=$RUN_DIR/$TASK_NAME/train

	meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR labels_dir=$LABELS_ROOT/$TASK_NAME \
		task_name=$TASK_NAME mode=predict dataset_type=supervised split=held_out \
		model_initialization_dir=$RUN_DIR/$TASK_NAME/train output_dir=$RUN_DIR/$TASK_NAME/predict

	meds-dev-evaluation predictions_dir=$RUN_DIR/$TASK_NAME/predict output_dir=$RUN_DIR/$TASK_NAME/evaluation
done
```

Passing `task_name` lets models that use `{task_criteria_path}` receive the task's registered criteria file.

**Full mode with a shared output directory.** Run `mode=full dataset_type=full` once per task with the
same `output_dir`, `dataset_name`, and `model`. Full mode lays out its stages as:

```
$RUN_DIR/$DATASET_NAME/unsupervised/train/   # shared by all tasks
$RUN_DIR/$DATASET_NAME/$TASK_NAME/train/
$RUN_DIR/$DATASET_NAME/$TASK_NAME/predict/
```

Every stage writes a `.done` marker when it finishes, and a stage whose directory already has one is
skipped. Pre-training therefore runs for the first task only; later tasks reuse it. Stages whose command is
`null` (for example `supervised.train` of a zero-shot model) are skipped, and `model_initialization_dir` then
still points at the pre-training directory.

> [!WARNING]
> Do not set `do_overwrite=true` when reusing a pre-trained model. It clears the whole `output_dir`
> (except its `.logs` directory) before anything runs, and also clears each stage's directory before running it. In full mode this deletes
> the shared pre-training stage and the results of every other task, so pre-training runs again.
>
> Run the tasks one after another. Two runs started at the same time on a shared `output_dir` can both
> start pre-training before either writes its `.done` marker.

### Evaluating predictions

To evaluate the predictions of a model on a task, you can use the `meds-dev-evaluation` helper. Point it
at your predictions in one of two ways:

```bash
# A directory of predictions, such as the output_dir of a `meds-dev-model` predict run:
meds-dev-evaluation predictions_dir=$PREDICTIONS_DIR output_dir=$EVALUATION_DIR

# A single predictions parquet file:
meds-dev-evaluation predictions_path=$PREDICTIONS_DIR/predictions.parquet output_dir=$EVALUATION_DIR
```

`predictions_dir` must be a directory: it is expanded to `predictions_path=$PREDICTIONS_DIR/**/*.parquet`,
so _every_ parquet file anywhere below that directory is read and evaluated together. Don't point it at a
directory that also holds other parquet files (e.g., predictions for another split), and don't pass a file
path to it. To evaluate exactly one file, set `predictions_path` instead; it also accepts a glob pattern.

The output JSON file from MEDS-Evaluation will contain the results of the evaluation, including the AUROC,
which is the primary metric for MEDS-DEV at this time.

### Re-running commands and `do_overwrite`

`meds-dev-dataset`, `meds-dev-task`, `meds-dev-model`, and `meds-dev-evaluation` are all safe to re-run:

- When a command succeeds, it writes an empty `.done` file to its `output_dir`. A later run with the same
    `output_dir` sees that file and skips the work, _even if you changed other arguments_. With `mode=full`,
    `meds-dev-model` tracks this per stage, so a re-run resumes at the first stage that has not finished.
- If an earlier run did not finish, `meds-dev-dataset` and `meds-dev-model` refuse to run a different
    command than the one saved in `output_dir/cmd.sh`, so outputs from two configurations never get mixed.
- `do_overwrite=True` deletes everything in `output_dir` before running, so the command starts from
    scratch. The `.logs` directory, which holds the current run's logs, is kept. For `meds-dev-model`, this
    also deletes the model's virtual environment, which lives in `output_dir/.venv` unless you set
    `venv_dir`. `meds-dev-dataset` never deletes `raw_input_dir`.

### Adding your result to MEDS-DEV

If you successfully run the sequence of stages above on a new dataset not yet included in MEDS-DEV -- let us
know and we'll happily help you add your dataset's information (but no sensitive data) and these results to
the public record to help advance the science of Health AI!

For an overview of how submissions, datasets, tasks, and models flow from this repository to the
[MEDS website](https://medical-event-data-standard.github.io) leaderboard — and how to debug or manually
trigger the pipeline — see [`src/MEDS_DEV/web/README.md`](src/MEDS_DEV/web/README.md).

## Contributing New Things to MEDS-DEV

> [!NOTE]
> See the [templates](templates) folder for templates for the README files for new tasks, datasets, or models!

### Adding a dataset

To add a dataset, you will need to create a new directory under `src/MEDS_DEV/datasets/` with the name of the
dataset, containing the following files:

1. `README.md`: This file should contain a description of the dataset. See the [templates](templates) for examples.
2. `requirements.txt`: This file should be a valid `pip` specification for what is needed to install the ETL
    to build the environment. _The ETL must be runnable on Python 3.11_.
3. `dataset.yaml`: This file needs to have two keys: `metadata` and `commands`. Under `commands`, you must
    have `build_full` and may provide `build_demo`. These commands, when run with their requirements installed,
    with the specified placeholder variables (indicated in python syntax, include `temp_dir` for intermediate
    files, `raw_input_dir` for the raw source data, and `output_dir` for where you want the final MEDS cohort
    to live) will produce the desired MEDS cohort. The `metadata` key should contain information about the dataset. See the `MIMIC-IV` dataset for an
    example of the allowed syntax here. Mandatory keys include `description`, `access_policy`, and the key
    `contacts` with at least one entry. Note that the values for `access_policy` are restricted to the values
    of the `AccessPolicy` `StrEnum` in the `MEDS_DEV.datasets` codebase, namely:
    - `"public_with_approval"`: Data that can be used (in principle) by anyone, but requires approval to access.
    - `"public_unrestricted"`: Data that can be used by anyone with no restrictions or gating.
    - `"institutional"`: Data that is only available within a specific institution or department, but is in
        principle accessible to all researchers within that group. This should not be used for data that has
        only been approved for a single group or a single research process.
    - `"private_single_use"`: Data that is only available to a single research group or project, and is not
        available nor likely to ever become available outside of that limited context.
    - `"other"`: Any other access mode that does not fit into the above categories. If you use this, you must
        describe the access policy in more details in the `access_details` optional field in the metadata.
4. `predicates.yaml` contains ACES syntax predicates to realize the target tasks.
5. Optionally, you should add a `refs.bib` file with a BibTex entry users should cite when they use the
    dataset.

If all of these are defined, then you can, after installing `MEDS-DEV` via `pip install -e .`, run the command
`meds-dev-dataset dataset=DATASET_NAME output_dir=OUTPUT_DIR` to generate the MEDS cohort for that dataset
(with `demo=True` if you want the demo version).

### Adding a task

To add a task, simply create a new task configuration file under `src/MEDS_DEV/tasks` with the desired
(slash-separated) task name. The task configuration file should be a valid ACES configuration file, with the
predicates left as placeholders to-be-overwritten by dataset-specific predicates. In addition, in the same
series of folders leading to the task configuration file, you should have `README.md` files that describe what
those "categories" of tasks mean. Note you can also specify a `refs.bib` file here, like with a dataset.

Once a task is defined, then you can, after installing `MEDS-DEV` via `pip install -e .`, run the command
`meds-dev-task task=TASK_NAME dataset=DATASET_NAME output_dir=OUTPUT_DIR dataset_dir=DATASET_DIR` to generate
the labels for task `TASK_NAME` over dataset `DATASET_NAME` stored in the directory `DATASET_DIR` in the
output directory `OUTPUT_DIR`.

You should also specify meaningful metadata about the task in the `metadata` key of the task configuration.
This metadata should include a list of datasets that the task is applicable to, e.g.,

```yaml
metadata:
  description: >-
    A description of your task
  contacts:
    - name: Your name
      github_username: Your GitHub username
  supported_datasets:
    - MIMIC-IV
    - '...'
```

The datasets you highlight in the `supported_datasets` key will also be used to test this task config against
the supported MEDS-DEV datasets.

### Adding a model

To add a model, create a new subdirectory of `src/MEDS_DEV/models/` with the name of the model. Then, within
this subdirectory, create a `requirements.txt`, `README.md`, and `model.yaml` file. The `requirements.txt`
contains the necessary Python packages to install to run the model, similar to dataset creation, the
`README.md` contains a description of the model, and the `model.yaml` file contains some programmatic
information about the model, including most critically a `commands` key with a dictionary of commands needed
to run to train the model from scratch on a MEDS dataset. It also must include a `metadata` key with some
example of the metadata. See the existing models for examples. Note you can also specify a `refs.bib` file
here, like with a dataset.

A full description of these commands is coming soon, but for now, note that:

1. Commands can use the template variables `{output_dir}`, `{dataset_dir}`, `{labels_dir}`, and `{demo}`.
    Models that need a dataset's predicates file (e.g., for featurization) can also use the optional
    `{predicates_path}` template variable, populated from the `predicates_path` argument to `meds-dev-model`.
    Models that predict a task from its definition rather than its labels (e.g., zero-shot models) can use
    the optional `{task_criteria_path}` template variable: the task's ACES criteria file, from the
    `task_criteria_path` argument or, by default, the registered criteria file of `task_name`.
2. Commands should be added in a nested manner for running either over `unsupervised` or `supervised`
    datasets, in either `train` or `predict` modes. See the random predictors example for an example.
    Put task-independent work (e.g., pre-training) under `unsupervised`, so it runs once per dataset, and
    task-dependent work under `supervised`; see
    [What `unsupervised` and `supervised` mean](#what-unsupervised-and-supervised-mean).

> [!TIP]
> To start a new model, consider the
> [MEDS algorithm template](https://github.com/McDermottHealthAI/MEDS_algorithm_template). It generates a
> repository with a standard command-line interface for six profiles (`supervised`, `finetune`, `probe`,
> `zero_shot_direct`, `zero_shot_materialized`, `predict_only`), conformance tests that run the model
> through MEDS-DEV, and one `model.yaml` per profile. Register a profile with:
>
> ```bash
> meds-algorithm-add-to-meds-dev --meds-dev /path/to/MEDS-DEV --name my_model --profile probe
> ```
>
> which adds it as the `my_model__probe` model. The template is optional: any `model.yaml` that follows the
> structure above can be added.

See the help string for `meds-dev-model` for more information. Note the final output predictions should be
stored as a set of parquet files in the final output directory specified by the `output_dir` variable in the
format expected by `meds-evaluation`.

#### `model.yaml` version 2: explicit steps

> [!NOTE]
> Version 2 is optional. Existing `model.yaml` files (version 1, the four slots above) keep working unchanged.

With the four slots above, a model with more steps than slots has to group several steps into one slot.
Task-independent work grouped into a `supervised` slot (e.g., preprocessing or computing embeddings) is then
repeated for every task. A version 2 `model.yaml` instead lists the model's steps explicitly:

```yaml
schema_version: 2
metadata: {'...': null}
profile: probe # optional; enables extra checks (see below)
steps:
  preprocess_data:
    scope: dataset # task-independent: run once per dataset, shared by every task
    command: my-model preprocess input={dataset_dir} 
      predicates={predicates_path} output={step_dir}
  pretrain:
    scope: dataset
    needs: [preprocess_data]
    command: my-model pretrain data={preprocess_data_dir} output={step_dir}
  infer_embeddings:
    scope: task # run once per task
    needs: [preprocess_data, pretrain]
    command: my-model embed data={preprocess_data_dir} encoder={pretrain_dir} 
      index={labels_dir} output={step_dir}
  train_probe:
    scope: task
    needs: [infer_embeddings]
    command: my-model train_probe embeddings={infer_embeddings_dir} 
      labels={labels_dir} output={step_dir}
  predict_probe:
    scope: task
    needs: [infer_embeddings, train_probe]
    predict: true # exactly one step; its output is evaluated
    command: my-model predict embeddings={infer_embeddings_dir} 
      probe={train_probe_dir} split={split} output={step_dir}
```

Each step has a `scope` (`dataset` or `task`), a `command`, optionally `needs` (earlier steps whose outputs
it reads), and exactly one task-scoped step sets `predict: true`. Commands can use:

| Template variable                                             | Available in       | Value                                      |
| ------------------------------------------------------------- | ------------------ | ------------------------------------------ |
| `{dataset_dir}`, `{model_dir}`, `{demo}`, `{predicates_path}` | every step         | as in version 1                            |
| `{step_dir}`                                                  | every step         | this step's output directory               |
| `{<step>_dir}`                                                | steps that need it | the output directory of that earlier step  |
| `{labels_dir}`, `{task_criteria_path}`                        | task-scoped steps  | as in version 1                            |
| `{split}`                                                     | the predict step   | the split to predict (default: `held_out`) |

`{output_dir}` and `{model_initialization_dir}` are not used in version 2: each step writes to `{step_dir}`
and reads the outputs of the steps it needs. These rules are checked when MEDS-DEV loads the model, so a
dataset-scoped step cannot use `{labels_dir}` and no step can read an output it did not declare.

Steps are stored under `<output_dir>/<dataset_name>/`:

```
_shared/<step>/output/        # dataset-scoped steps, shared by every task
<task_name>/<step>/output/    # task-scoped steps
<task_name>/predict/output/   # the predict step (held-out split)
```

MEDS-DEV keeps its own files (`cmd.sh`, `.done`) in `<step>/`, next to the step's `output/`. Finished steps
are skipped, and shared steps are locked while they run, so several tasks can run at the same time on the
same `output_dir`. `dataset_name` must be set, and `task_name` (or `tasks`) whenever task-scoped steps run.

Running a version 2 model:

```bash
# Every step for one task (shared steps are reused if they already ran)
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR dataset_name=$DATASET_NAME \
	task_name=$TASK_NAME labels_dir=$LABELS_DIR predicates_path=$PREDICATES mode=full dataset_type=full \
	output_dir=$RUN_DIR

# Several tasks in one call: shared steps run once; labels are read from labels_root/<task>
meds-dev-model model=$MODEL_NAME dataset_dir=$DATASET_DIR dataset_name=$DATASET_NAME \
	'tasks=[task_a,task_b]' labels_root=$LABELS_ROOT mode=full dataset_type=full output_dir=$RUN_DIR

# Only some steps (plus the steps they need), reusing an existing output for one of them
meds-dev-model ... 'steps=[predict_probe]' +step_dirs.pretrain=/path/to/pretrain/output
```

`dataset_type` and `mode` select steps as in version 1 (`unsupervised` selects the dataset-scoped steps,
`supervised` the task-scoped ones; `train` the steps before the predict step, `predict` the predict step),
plus every step they need. `model_initialization_dir` points at the `output_dir` of an earlier run whose
shared steps should be reused. `overwrite=task` clears this run's task-scoped steps but keeps the shared ones;
`overwrite=all` (or `do_overwrite=true`) clears every step the run executes, but never the rest of
`output_dir`.

If `profile` is set, MEDS-DEV also checks the steps against it:

| `profile`                | Check                                                                                                                        |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| `supervised`             | at least one task-scoped training step before the predict step                                                               |
| `finetune`, `probe`      | at least one dataset-scoped step, and at least one task-scoped training step                                                 |
| `zero_shot_direct`       | at least one dataset-scoped step; no task-scoped step besides the predict step; the predict step uses `{task_criteria_path}` |
| `zero_shot_materialized` | at least one dataset-scoped step; the predict step uses `{task_criteria_path}`                                               |
| `predict_only`           | no task-scoped step besides the predict step                                                                                 |

## Efficient Testing

To make testing more efficient during model / task development, you can use a local, persistent cache dir to
avoid repeating the parts of the test setup you aren't changing. To do this, use the following command line
arguments with pytest:

```bash
pytest --doctest-modules -s --persistent_cache_dir=$TEST_CACHE --cache_dataset='all' --cache_task='all'
```

Note that

1. The `--persistent_cache_dir` argument specifies the directory where the cache will be stored. It must be an
    existing directory on disk.
2. You can either specify `--cache_dataset`, `--cache_task`, and/or `--cache_model` with a list of specific
    datasets, models, or tasks to cache by using the argument multiple times with the specific names, or you
    can use `'all'` to cache all datasets, models, or tasks, as is shown above.
3. The cached parts specified via the arguments will be stored in the persistent cache directory; other parts
    will be stored in temporary directories and deleted in between runs. Persistently cached parts will not be
    re-run, even if the associated code for that part is changed. So, you need to manually ensure that you are
    only caching things that won't change with your code.

You can also restrict the set of tasks, datasets, and models that you explore using the command line options
`--test_task`, `--test_dataset`, and `--test_model`, respectively. These options can be used to run only the
selected options (repeating the argument as needed, e.g., `--test_task=task1 --test_task=task2`). If they are
omitted or if `'all'` is specified as an option, then all allowed tests will be run.

Note that _caching does not imply that test code will not be re-run_ -- instead, it just ensures that output
files are stored on disk in the specified directory. For some aspects of MEDS-DEV, this means that test-code
will be re-run and files replaced; for others, it will be reused. This is a feature, not a bug, as it allows
you to inspect output files while reliably re-testing code. However, if you want to fully reuse a component
of a test, you can also specify the additional arguments: `--reuse_cached_dataset`, `--reuse_cached_task`, or
`--reuse_cached_model` with the same syntax of the `--cache_*` and `--test_*` arguments. Then, the test code
will explicitly mark the specified components within the persistent cache directory as "reusable" and will
not re-run the associated MEDS-DEV code pipelines in between test runs, but simply reuse the outputs.

By default, even when caching is enabled, the testing code will clear the virtual environments of the various
model and dataset runs after they are no longer needed, to reduce the overall disk footprint of the test
suite. You can disable this by adding the argument `--no_do_clear_venvs` to the pytest command line.

## Notes

1. Some models in this repo use Hugging Face Datasets objects. These cache data to disk in a directory you
    can control via the environment variable `HF_DATASETS_CACHE`. If you have disk space or security concerns
    about storage in the ordinary cache directory, you should set this variable manually to a desired
    directory in your terminal before running MEDS-DEV commands. See #144 for more details.
