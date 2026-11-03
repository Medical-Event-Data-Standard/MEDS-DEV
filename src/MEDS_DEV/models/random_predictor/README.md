# Random Predictor

This is a random, dummy predictor for use primarily in testing. It literally just spits out random
predictions. The predictions are not calibrated to the base rate of the task, they are truly just random with
a chance value of 0.5.

Its command also demonstrates how a model can receive the current dataset's predicate definitions through
the `{predicates_path}` template variable. The predictor does not use those definitions to generate its
baseline, but verifies that the configured file exists.
