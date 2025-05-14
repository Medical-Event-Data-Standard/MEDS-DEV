# [New model] \*\*Add your model name here\*\*

> [!WARNING]
> MEDS-DEV currently only supports binary classification tasks and therefore only accepts binary
> classification models for now.

## Description

Provide a brief description of your model, including:

- Model architecture and key components
- Intended purpose and target tasks
- Any notable features or innovations
- Limitations or constraints

## Computational Requirements

Provide information about the computational requirements of your model, including:

- Hardware specifications used during testing (e.g., GPU type, memory)
- Computational resources required for training and inference
- Performance characteristics (e.g., training speed)

## Dependencies

List all dependencies required to run your model. For each dependency, provide:

- Name of the dependency
- Version number (if applicable)
- Any specific installation instructions (if needed)

Example:

- Python 3.8+
- TensorFlow 2.4.0
- NumPy 1.19.5
- Pandas 1.2.0

## Additional Requirements

For each additional requirement, please provide:

- **What is the requirement**: Describe the dependency (e.g., SNOMED codes, knowledge graphs, LOINC codes,
    local SQL databases).
- **What is it used for**: Explain the purpose of the requirement within your model.
- **How do you set it up (installation and filepath information)**: Provide detailed setup instructions, including installation steps and file path configurations.
- **How do you use it**: Describe how to interact with the requirement after setup.

## Running the model

Please provide detailed instructions for running your model, including:

- Installation steps
- Command-line instructions or API usage
- Description of all CLI arguments and their default values
- Expected output format (where the best checkpoint is stored, where predictions are stored, etc.)
- Description of all parameters and their default values
- Troubleshooting tips (if applicable)

## Resources and links

Please provide the following:

- Link to the model's implementation repository
- Link to the model's documentation (if separate from the repository)
- Any relevant research papers or articles
- Links to pre-trained model weights (if applicable)
- Any additional resources that would be helpful for users

## Checklist

Please ensure your model conforms to the MEDS-DEV API by checking the following:

- [ ] It is compatible with the most recent version of the MEDS data format.
- [ ] Its outputs are compatible with the most recent version of the MEDS-evaluation schema.
- [ ] All required dependencies are clearly listed and versioned.
- [ ] The model can be run using the provided instructions without errors.
- [ ] The model documentation is complete and follows this template.
- [ ] (If applicable) The model has been tested on a sample dataset provided by MEDS-DEV.
