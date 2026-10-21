"""The mem command that uv installs into .venv/bin."""

import os
import subprocess
import sys
from pathlib import Path

BIN = Path(sys.prefix) / "bin" / "mem"


def launch(*args: str, cwd: Path, command: Path = BIN) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"NO_COLOR": "1"}
    return subprocess.run([command, *args], capture_output=True, text=True, cwd=cwd, env=env)


def test_help_lists_the_commands(tmp_path: Path):
    result = launch("--help", cwd=tmp_path)
    assert result.returncode == 0
    for command in ("status", "apps", "projects", "suggest"):
        assert f"  {command}" in result.stdout


def test_with_no_command_it_shows_the_status(tmp_path: Path):
    result = launch(cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Top apps" in result.stdout
    assert result.stdout.rstrip().splitlines()[-1].startswith("➖ Memory pressure ")


def test_it_works_through_a_symlink(tmp_path: Path):
    os.symlink(BIN, tmp_path / "mem")
    assert launch("--help", cwd=tmp_path, command=tmp_path / "mem").returncode == 0


def test_an_unknown_filter_is_a_precondition(tmp_path: Path):
    result = launch("apps", "no-such-app-anywhere", "--sample", "0.1", cwd=tmp_path)
    assert result.returncode == 1
    assert result.stderr == "⚠️ No app's name contains 'no-such-app-anywhere'.\n"


def test_an_idle_threshold_without_a_unit_is_a_usage_error(tmp_path: Path):
    assert launch("suggest", "--idle", "2", cwd=tmp_path).returncode == 2


def test_only_the_commands_that_judge_idleness_take_an_idle_threshold(tmp_path: Path):
    for command, takes in (
        ("status", True),
        ("suggest", True),
        ("apps", False),
        ("projects", False),
    ):
        assert ("--idle" in launch(command, "--help", cwd=tmp_path).stdout) == takes
