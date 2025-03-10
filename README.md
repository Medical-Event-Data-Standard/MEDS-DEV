# MEDS-DEV: Establishing Reproducibility and Comparability in Health AI

[![PyPI - Version](https://img.shields.io/pypi/v/MEDS-DEV)](https://pypi.org/project/MEDS-DEV/)
![python](https://img.shields.io/badge/-Python_3.11-blue?logo=python&logoColor=white)
[![codecov](https://codecov.io/gh/Medical-Event-Data-Standard/MEDS-DEV/graph/badge.svg?token=5RORKQOZF9)](https://codecov.io/gh/Medical-Event-Data-Standard/MEDS-DEV)
[![tests](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/tests.yaml/badge.svg)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/tests.yml)
[![code-quality](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/code-quality-main.yaml/badge.svg)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/actions/workflows/code-quality-main.yaml)
[![hydra](https://img.shields.io/badge/Config-Hydra_1.3-89b8cd)](https://hydra.cc/)
[![license](https://img.shields.io/badge/License-MIT-green.svg?labelColor=gray)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV#license)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/pulls)
[![contributors](https://img.shields.io/github/contributors/Medical-Event-Data-Standard/MEDS-DEV.svg)](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/graphs/contributors)

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

If you just want to reproduce MEDS-DEV models and tasks over public or your own, local datasets, you can
install MEDS-DEV from [PyPI](https://pypi.org/project/MEDS-DEV/) via `pip install MEDS-DEV`.

If you want to _contribute new models, tasks, or datasets_ to MEDS-DEV, you need to fork this repository,
clone your fork, and then install the repository locally in "editable" mode via `pip install -e .[dev,tests]`.
This will let you prepare your PR code and run the tests to ensure your contributions are valid and
transportable across MEDS-DEV datasets and tasks.

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

> \[!Note\]
> If your dataset is already extracted in the MEDS format, you can skip this step and assume that
> `$DATASET_DIR` points to the directory containing your MEDS-formatted dataset.

To build a supported dataset that you have access to in the MEDS format at the specified version used in
MEDS-DEV, you can use the `meds-dev-dataset` helper:

```bash
meds-dev-dataset dataset=$DATASET_NAME output_dir=$DATASET_DIR
```

where `DATASET_NAME` is the name of the dataset you want to build and `OUTPUT_DIR` is the directory where you
want to store the final, MEDS-formatted dataset.

> \[!NOTE\]
> Note that you can also specify `demo=True` to build a demo version of this dataset (if supported) for ease
> of testing the pipeline and your downstream code.

> \[!NOTE\]
> Note that here, `$DATASET_NAME` is the entire, slash-separated path from `src/MEDS_DEV/datasets/` to the
> directory containing the dataset's `commands.yaml` and `README.md` files. This name is a unique identifier
> for MEDS-DEV datasets so that the right task-specific predicates can be used and that it is clear what
> results were built on what dataset.

### Extracting a task

> \[!Note\]
> If your task labels are already extracted in the MEDS format, you can skip this step and assume that
> `$LABELS_DIR` points to the directory containing your MEDS-formatted task labels for the specific task of
> interest.

> \[!NOTE\]
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

> \[!Warning\]
> Right now, we don't have a good way to point to predicates files on disk that are used for datasets not yet
> configured for MEDS-DEV. File a new or up-vote any existing relevant GitHub issues for this functionality if
> it would be helpful for you! In general, we encourage that, eventually, any dataset over which MEDS-DEV
> results are reported publicly (e.g., in a publication) be added to MEDS-DEV (this does not necessitate data
> release -- merely that you include the predicate definitions used linked to a unique name, and ideally to
> the code you use to build the MEDS view of these data so others at your site can contribute in a
> reproducible way).

> \[!Note\]
> Note that here, `$TASK_NAME` is the entire, slash-separated path from `src/MEDS_DEV/tasks/` to the
> task configuration file. This name is a unique identifier for MEDS-DEV tasks.

> \[!Note\]
> Note that _it is guaranteeably true that not all tasks will be appropriate for or supported on all
> datasets._ Some tasks are only suited for certain clinical populations, which may not exist on all datasets.
> We're still figuring out the best way to operationalize this formally, but for now, please be cognizant of
> whether or not a task should be used on your dataset, and if you have ideas on this, don't hesitate to weigh
> in on [the GitHub Issue](https://github.com/Medical-Event-Data-Standard/MEDS-DEV/issues/60) about this!

### Using a model

> \[!Note\]
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

> \[!Note\]
> If you're a model creator, don't worry that you'll have to conform to this API -- this is just the API for
> model users, and internally MEDS-DEV wraps this API into whatever custom scripts and calls you need your
> model to take to train and predict. See the section below about "Contributing" for more details!

> \[!Note\]
> You can also run the full suite of supported commands for a model in the right order, chaining directories
> as needed, using the `mode=full` and `dataset_type=full` options. This will run the full sequence of
> commands in 1-3 above, and store the intermediate results in subdirectories of the output directory.

### Evaluating predictions

To evaluate the predictions of a model on a task, you can use the `meds-evaluation` helper:

```bash
meds-dev-evaluation predictions_dir=$PREDICTIONS_DIR output_dir=$EVALUATION_DIR
```

The output JSON file from MEDS-Evaluation will contain the results of the evaluation, including the AUROC,
which is the primary metric for MEDS-DEV at this time.

### Adding your result to MEDS-DEV

If you successfully run the sequence of stages above on a new dataset not yet included in MEDS-DEV -- let us
know and we'll happily help you add your dataset's information (but no sensitive data) and these results to
the public record to help advance the science of Health AI!

## Contributing New Things to MEDS-DEV

> \[!Note\]
> See the [templates](templates) folder for templates for the README files for new tasks, datasets, or models!

### Adding a dataset

To add a dataset, you will need to create a new directory under `src/MEDS_DEV/datasets/` with the name of the
dataset, containing the following files:

1. `README.md`: This file should contain a description of the dataset. See the [templates](templates) for examples.
2. `requirements.txt`: This file should be a valid `pip` specification for what is needed to install the ETL
    to build the environment. _The ETL must be runnable on Python 3.11_.
3. `dataset.yaml`: This file needs to have two keys: `metadata` and `commands`. Under `commands`, you must
    have the keys `build_full` and `build_demo` that, if run in an environment with the requirements installed,
    with the specified placeholder variables (indicated in python syntax, include `temp_dir` for intermediate
    files and `output_dir` for where you want the final MEDS cohort to live) will produce the desired MEDS
    cohort. The `metadata` key should contain information about the dataset. See the `MIMIC-IV` dataset for an
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
2. Commands should be added in a nested manner for running either over `unsupervised` or `supervised`
    datasets, in either `train` or `predict` modes. See the random predictors example for an example.

See the help string for `meds-dev-model` for more information. Note the final output predictions should be
stored as a set of parquet files in the final output directory specified by the `output_dir` variable in the
format expected by `meds-evaluation`.

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
will be re-run and files replaced; for others, it will be re-used. This is a feature, not a bug, as it allows
you to inspect output files while reliably re-testing code. However, if you want to fully re-use a component
of a test, you can also specify the additional arguments: `--reuse_cached_dataset`, `--reuse_cached_task`, or
`--reuse_cached_model` with the same syntax of the `--cache_*` and `--test_*` arguments. Then, the test code
will explicitly mark the specified components within the persistent cache directory as "re-useable" and will
not re-run the associated MEDS-DEV code pipelines in between test runs, but simply re-use the outputs.

By default, even when caching is enabled, the testing code will clear the virtual environments of the various
model and dataset runs after they are no longer needed, to reduce the overall disk footprint of the test
suite. You can disable this by adding the argument `--no_do_clear_venvs` to the pytest command line.

## Notes

1. Some models in this repo use Hugging Face Datasets objects. These cache data to disk in a directory you
    can control via the environment variable `HF_DATASETS_CACHE`. If you have disk space or security concerns
    about storage in the ordinary cache directory, you should set this variable manually to a desired
    directory in your terminal before running MEDS-DEV commands. See #144 for more details.
