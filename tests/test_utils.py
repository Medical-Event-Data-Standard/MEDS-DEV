"""Fast tests for the command-running helpers in `MEDS_DEV.utils`."""

import os

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


def test_run_in_env_sources_venv_activation(tmp_path):
    # The venv is activated inside cmd.sh, not only through the PATH in `env`, so shell startup files that
    # reorder PATH can't hide it. A path with a space checks that the activation line is quoted.
    venv_dir = tmp_path / "my venv"
    (venv_dir / "bin").mkdir(parents=True)
    (venv_dir / "bin" / "activate").write_text('export MEDS_DEV_TEST_ACTIVATED="yes"\n')
    output_dir = tmp_path / "output"
    env = {k: v for k, v in os.environ.items() if k != "MEDS_DEV_TEST_ACTIVATED"}
    env["VIRTUAL_ENV"] = str(venv_dir)

    run_in_env('echo "$MEDS_DEV_TEST_ACTIVATED" > activated.txt', output_dir, env=env, cwd=output_dir)

    assert (output_dir / "activated.txt").read_text().strip() == "yes"
    script_lines = (output_dir / "cmd.sh").read_text().splitlines()
    assert script_lines.index(f"source '{venv_dir}/bin/activate'") < script_lines.index(
        'echo "$MEDS_DEV_TEST_ACTIVATED" > activated.txt'
    )


def test_run_in_env_without_activation_script(tmp_path):
    # A VIRTUAL_ENV without a `bin/activate` (e.g., inherited from the caller) is not sourced.
    output_dir = tmp_path / "output"
    env = {**os.environ, "VIRTUAL_ENV": str(tmp_path / "not_a_venv")}

    run_in_env("touch new.parquet", output_dir, env=env, cwd=output_dir)

    assert (output_dir / "new.parquet").is_file()
    assert "source" not in (output_dir / "cmd.sh").read_text()
