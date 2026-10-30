"""Fast tests for the command-running helpers in `MEDS_DEV.utils`."""

from MEDS_DEV.utils import run_in_env


def test_run_in_env_skips_done_output_dir(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / ".done").touch()

    run_in_env("touch new.parquet", output_dir, cwd=output_dir)

    assert not (output_dir / "new.parquet").exists()


def test_run_in_env_overwrite_keeps_hydra_logs(tmp_path):
    output_dir = tmp_path / "output"
    (output_dir / ".logs").mkdir(parents=True)
    (output_dir / ".logs" / "run.log").write_text("current run log")
    (output_dir / "stale.parquet").write_text("stale output")
    (output_dir / ".done").touch()

    run_in_env("touch new.parquet", output_dir, do_overwrite=True, cwd=output_dir)

    assert sorted(p.name for p in output_dir.iterdir()) == [".done", ".logs", "cmd.sh", "new.parquet"]
    assert (output_dir / ".logs" / "run.log").read_text() == "current run log"
