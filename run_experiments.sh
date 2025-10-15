#!/bin/bash

# Define the datasets and tasks
datasets=(
    "AUMCdb"
    "eICU"
    "EHRShot"
    "HIRID"
    "INSPIRE"
    "MIMIC-IV"
    "NWICU"
    "SICdb"
)

tasks=(
    "abnormal_lab/vital/hypotension/first_24h"
    "abnormal_lab/blood_chemistry/metabolic_acidosis/first_24h"
    "abnormal_lab/blood_chemistry/hyponatremia/first_24h"
    "abnormal_lab/blood_chemistry/elevated_creatinine/first_24h"
    "abnormal_lab/cbc/leukocytosis/first_24h"
    "abnormal_lab/cbc/thrombocytopenia/first_24h"
    "abnormal_lab/cbc/anemia/first_24h"
    "mortality/in_icu/first_24h"
    "readmission/general_hospital/30d"
)

# Base directory for datasets
base_dir="/Users/robin/Documents/datasets/meds"

# Loop through datasets and tasks
for dataset in "${datasets[@]}"; do
    export DATASET_NAME=$dataset
    export DATASET_DIR="$base_dir/$dataset"

    for task in "${tasks[@]}"; do
        echo "Processing dataset: $DATASET_NAME, task: $task"
        export TASK_NAME=$task
        export LABELS_DIR="$DATASET_DIR/labels/$task"

        # Run the meds-dev-task command
        meds-dev-task task="$TASK_NAME" dataset="$DATASET_NAME" output_dir="$LABELS_DIR" dataset_dir="$DATASET_DIR"

        echo "Completed dataset: $DATASET_NAME, task: $task"
    done
done
