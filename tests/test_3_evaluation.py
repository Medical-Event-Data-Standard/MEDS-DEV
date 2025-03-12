import json
from pathlib import Path


def test_evaluates(evaluated_model: Path):
    evaluation_dir = evaluated_model

    try:
        assert evaluation_dir.exists(), "Evaluation dir should exist"
        assert len(list(evaluation_dir.rglob("*.json"))) == 1, "There should only be one result file."
        eval_fp = evaluation_dir / "results.json"
        assert eval_fp.is_file(), "The result file should exist"
        try:
            eval_results = json.loads(eval_fp.read_text())
        except json.JSONDecodeError as e:
            raise AssertionError(f"Results file {eval_fp} should be a valid JSON file.") from e
        assert type(eval_results) is dict, "Results should be a dictionary"
        assert len(eval_results) > 0, "Results should not be empty"
    except AssertionError as e:
        error_lines = [
            f"Output directory {evaluation_dir} check failed. Walking back...",
        ]
        d = evaluation_dir.parent
        while not d.exists():
            error_lines.append(f"Directory {d} does not exist.")
            d = d.parent
        error_lines.append(f"Directory {d} exists. Contents:")
        error_lines.append(str(list(d.rglob("*"))))
        raise AssertionError("\n".join(error_lines)) from e
