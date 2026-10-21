from pathlib import Path

import pytest

from mem.model import Proc


@pytest.fixture
def proc():
    """Makes a Proc, with defaults for whatever a test doesn't care about."""

    def make(pid: int, ppid: int = 1, name: str = "", exe: str = "", **fields) -> Proc:
        name = name or Path(exe).name or f"proc{pid}"
        fields = {"cmdline": [exe or name], "cwd": None, "memory": 0, "started": 0.0} | fields
        return Proc(pid=pid, ppid=ppid, name=name, exe=exe, **fields)

    return make
