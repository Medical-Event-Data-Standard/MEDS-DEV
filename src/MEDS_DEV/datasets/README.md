# Datasets

This folder contains details for datasets currently included in the MEDS-DEV effort.

To contribute a new dataset:

1. Fork this repository
2. Add your dataset predicates file in its respective folder (see `MIMIC-IV/predicates.yaml` for an example of predicate structure)
3. Test locally to ensure your dataset works correctly. Ideally specify the used packages and versions in the dataset information.
4. Specify the dataset information (including supported and custom tasks) in the template README.md file in the dataset's folder.
5. Create a pull request with your changes

## Demo predicate coverage

Dataset integration tests require every plain predicate code matcher to match at least one event in the demo.
If a valid full-dataset code is absent from the demo, add a documented exception to `dataset.yaml`:

```yaml
testing:
  demo:
    allowed_uncovered_predicate_codes:
      CODE//ABSENT_FROM_DEMO: >-
        Explain why this code is valid for the full dataset but absent from the demo.
```

Use exceptions only for exact codes that are valid in the full dataset. Every exception requires a reason,
must be referenced by a plain predicate, and must be removed if a future demo starts covering that code.

## Notes

If you have a version of a task configuration file that is more specialized to a dataset than can be achieved
with overwriting the predicates alone, then:

1. Make a GitHub issue explaining why the existing file is not used
2. Add a file here `../tasks/$DATASET_NAME/$TASK_NAME.yaml` with that configuration.
