# [New result] {task}, {dataset}, {model}

*Replace the {task}, {dataset}, and {model} above with the actual names as appropriate*

Users are expected to submit one pull request for each (task × dataset × model) combination.

In this pull request, one file should be added with the following structure:

```yaml
meds_dev_version: ??? # e.g., v1.0.0
task_name: ??? # follows the MEDS-DEV task directory structure, e.g. "criteria/mortality/in_icu/first_24h"
dataset: ??? # follows the MEDS-DEV dataset directory name, e.g. "MIMIC-IV"
model: ??? # follows the MEDS-DEV model directory name
metrics:
  auc: ???
  # TODO: this should follow the structure of meds-evaluation output.
```

This file should be located in `src/MEDS_DEV/results/${meds_dev_version}/${task}/${dataset}/${model}.yaml`.

TODO: the `metrics` field (and most of the submitted YAML configuration) should ideally be directly based on the output of the [`meds-evaluation`](https://github.com/kamilest/meds-evaluation) package—it should be possible to submit the output file directly with minimal to no manual modification.

> [!WARNING]
> TODO: In the future updates, a GitHub Action will validate the results YAML using the following criteria:
>
> 1. The (task × dataset × model) is new to MEDS-DEV.
> 2. The (task × dataset × model) combination is sound (e.g. the dataset supports the task).
> 3. All supported task-specific metrics are included.
> 4. The submitted YAML configuration contains all of the expected fields.

## Retracted results

To retract a result, the user is expected to submit a pull request that removes the result, with the explanation why.
