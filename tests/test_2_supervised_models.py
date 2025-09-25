from tests.utils import NAME_AND_DIR


def test_supervised(
    supervised_model: NAME_AND_DIR,
    demo_dataset: NAME_AND_DIR,
    task_labels: NAME_AND_DIR,
):
    model, final_out_dir = supervised_model
    dataset_name, _ = demo_dataset
    task_name, _ = task_labels
    setting = f"{model} for {task_name} on {dataset_name}"

    if not final_out_dir.exists():
        error_lines = [
            f"Output directory {final_out_dir} does not exist for {setting}.",
            f"Model {model} for {task_name} on {dataset_name} did not run properly. Walking back...",
        ]
        d = final_out_dir.parent
        while not d.exists():
            error_lines.append(f"Directory {d} does not exist.")
            d = d.parent
        error_lines.append(f"Directory {d} exists. Contents:")
        error_lines.append(str(list(d.rglob("*"))))
        raise AssertionError("\n".join(error_lines))

    predict_dir = final_out_dir / "predict"

    assert len(list(predict_dir.rglob("*.parquet"))) > 0, f"No predictions written for {setting}."
