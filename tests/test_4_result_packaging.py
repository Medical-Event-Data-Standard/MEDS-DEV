import random
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from MEDS_DEV import __version__ as MEDS_DEV_version
from MEDS_DEV.results import Result


def test_validate_result_error():
    def run(result_fp: Path):
        cmd = ["meds-dev-validate-result", f"result_fp={result_fp}"]
        return subprocess.run(cmd, check=False, capture_output=True)

    with tempfile.TemporaryDirectory() as tempdir:
        non_existent_fp = Path(tempdir) / "non_existent.json"
        out = run(non_existent_fp)
        assert out.returncode != 0, "Validation should fail for non-existent file"
        assert f"FileNotFoundError: File not found: {str(non_existent_fp)}" in out.stderr.decode()

    with tempfile.NamedTemporaryFile(suffix=".json") as temp:
        temp.write(b"")
        temp.flush()

        out = run(Path(temp.name))
        assert out.returncode != 0, "Validation should fail for empty file"
        assert "json.decoder.JSONDecodeError" in out.stderr.decode()

        # Let's make sure it passes for a valid file
        fake_result = Result(
            dataset="fake",
            task="fake",
            model="fake",
            version="fake",
            timestamp=datetime.now(),
            result={
                "per_patient": {"roc_auc_score": 0.5},
                "per_sample": {"roc_auc_score": 0.5},
            },
        )
        fake_result.to_json(temp.name, do_overwrite=True)
        out = run(Path(temp.name))
        assert out.returncode == 0, "Validation should pass for valid file"

        # Now we'll check that it fails if the file is too large, which may indicate that there is too much
        # data in the result.
        arr = [random.random() for _ in range(100000)]
        fake_result.result["per_patient"]["roc_auc_score"] = arr
        fake_result.to_json(temp.name, do_overwrite=True)
        file_size_kb = Path(temp.name).stat().st_size / 1024
        out = run(Path(temp.name))
        assert out.returncode != 0, "Validation should fail for large file"
        assert f"ValueError: Result file is too large ({file_size_kb:.2f} KB > 1.5 KB)" in out.stderr.decode()


def test_pack_result_error():
    with tempfile.TemporaryDirectory() as tempdir:
        non_existent_fp = Path(tempdir) / "non_existent.json"
        out = subprocess.run(
            ["meds-dev-pack-result", f"evaluation_fp={non_existent_fp}"],
            check=False,
            capture_output=True,
        )
        assert out.returncode != 0, "Packaging should fail for non-existent file"
        assert f"FileNotFoundError: File not found: {str(non_existent_fp)}" in out.stderr.decode()


def test_packages_result(packaged_result: Path):
    results_fp = packaged_result

    try:
        result = Result.from_json(results_fp)
    except Exception as e:
        raise AssertionError("Result should be packaged and decodable") from e

    assert result.version == MEDS_DEV_version

    ts = result.timestamp
    now = datetime.now(ts.tzinfo)
    assert ts < now and ts > now - timedelta(hours=2)

    try:
        subprocess.run(["meds-dev-validate-result", f"result_fp={results_fp}"], check=True)
    except subprocess.CalledProcessError as e:
        raise AssertionError("Result should be valid according to MEDS-DEV validator") from e
