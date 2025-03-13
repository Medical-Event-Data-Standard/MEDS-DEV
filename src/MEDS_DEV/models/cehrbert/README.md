# CEHR-BERT Predictor

For detailed cehr-bert documentation, please visit repo at https://github.com/cumc-dbmi/cehrbert.

> \[!WARNING\]
> This model is currently very disk intensive, both in pre-processed datasets and in the huggingface datasets
> cache. Please ensure you have enough disk space to run this model. Note that you can change the huggingface
> cache directory by setting the `HF_DATASETS_CACHE` environment variable prior to training this model;
> setting it to `/dev/null` will _cause the system to error out_ so you should instead set it to a real
> directory and ensure that disk has sufficient room for the cached files. See
> https://github.com/Medical-Event-Data-Standard/MEDS-DEV/issues/134 and
> https://github.com/cumc-dbmi/cehrbert/issues/93 for more information.
