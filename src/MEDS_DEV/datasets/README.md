# Datasets

This folder contains details for datasets currently included in the MEDS-DEV effort.

To contribute a new dataset:

1. Fork this repository
2. Add your dataset predicates file in its respective folder (see `MIMIC-IV/predicates.yaml` for an example of predicate structure)
3. Test locally to ensure your dataset works correctly. Ideally specify the used packages and versions in the dataset information.
4. Specify the dataset information (including supported and custom tasks) in the template README.md file in the dataset's folder.
5. Create a pull request with your changes

## Notes

If you have a version of a task configuration file that is more specialized to a dataset than can be achieved
with overwriting the predicates alone, then:

1. Make a GitHub issue explaining why the existing file is not used
2. Add a file here `../tasks/$DATASET_NAME/$TASK_NAME.yaml` with that configuration.
