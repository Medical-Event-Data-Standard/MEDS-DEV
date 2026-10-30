# GenHPF Predictor for MEDS dataset

For detailed documentation for GenHPF model, please refer to [https://github.com/hoon9405/GenHPF](https://github.com/hoon9405/GenHPF).

## Known limitations

GenHPF encodes every number in an event's text with a digit-place embedding that only has room for 10 digits
before the decimal point. Numbers with more integer digits (i.e., values of 10,000,000,000 or larger) produce
out-of-range embedding indices, and training crashes with an index error. This applies to any run of digits
in the event text: numeric values, but also digits embedded in codes or text values. If your dataset contains
such values, clip or remove them before running this model.
