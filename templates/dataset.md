# [New dataset] \*\*Add your dataset name here\*\*

This is a template for supporting a new dataset in MEDS-DEV. Please edit the information on the template as appropriate, and commit this information in a `README.md` file in a directory named after your dataset in `src/MEDS_DEV/datasets` (e.g. `src/MEDS_DEV/datasets/MIMIC-IV/README.md`).

## Description

Provide a brief description of your dataset, including:

- Aggregate statistics (e.g., number of patients, time range, age distributions, demographic distributions)
- Cohort description:
    - Inclusion/exclusion criteria
    - Censoring rules
    - Key demographic characteristics
- Date range of the dataset (e.g. patients at hospital A from 2013-2023)
- Coding standards, if known (e.g. OMOP)

## Supported tasks

Provide the list of the existing tasks already present in MEDS-DEV that are covered, and note any exceptions for tasks that **cannot** be run on your dataset (e.g. due to censoring limitations, incompatible inclusion criteria, etc.)

For supported tasks, provide the predicate definitions in a `predicates.yaml` file in `src/MEDS_DEV/datasets/$YOUR_DATASET_NAME` (e.g. `src/MEDS_DEV/datasets/MIMIC-IV/predicates.yaml`).

### Future tasks

If there are any currently undefined tasks that your dataset would be particularly suitable for, describe them here.

## Resources and links

Please provide the following:

- Link to the dataset's webpage and/or documentation (e.g., institutional repository, GitHub)
- Relevant research papers or articles, e.g.:
    - Original dataset publication
    - Key studies using this dataset
    - Methodology papers
- Additional resources, e.g.:
    - Data dictionaries
    - Code repositories
    - Usage examples

## Access requirements

Describe any access requirements for the dataset (e.g, human species research). If the dataset is publicly available, state that here. If the dataset is not publicly available, describe the process for obtaining access and using the dataset (including any APIs and points of contact to send any models to for evaluation).

We recommend the following topics be covered:

- **Access policy**: Describe the access policy for the dataset, including any restrictions or permissions required.
- **License (for files)**: Specify the license under which the dataset files are distributed.
- **Data use agreement**: Specify any data use agreement that must be signed to access the dataset.
- **Required training**: Specify any training or certification required to access the dataset.
- **Point of contact**: Include a point of contact to send any queries about the dataset to (especially for private datasets).

## MEDS compatibility

Shortly specify the process of transforming this dataset into the MEDS format. If the dataset is already in the MEDS format when downloaded, specify that here.

Provide any other instructions for how to prepare the dataset for use with MEDS models and tasks.

## Checklist

Please ensure your model conforms to the MEDS-DEV API by checking the following:

- [ ] I filled out the above template and committed it as a `README.md` file in a directory named after the dataset in `src/MEDS_DEV/datasets`.
- [ ] I included the `predicates.yaml` file, defining all predictates required for the supported tasks.
- [ ] I verified all resource links are permanent and accessible to the public.
- [ ] I included example usage code and API instructions (if applicable).
- [ ] I documented any known limitations or biases in the dataset.
- [ ] I specified the dataset version or date of the last update.
