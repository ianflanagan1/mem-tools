"""A snapshot of every process the user can see, with its memory and the CPU it used during a
short sample, which tells idle processes from busy ones."""

import ctypes
import re
import sys
import time
from pathlib import Path

import psutil

from mem.model import Proc

_ATTRS = ["pid", "ppid", "name", "exe", "cmdline", "cwd", "create_time", "username", "memory_info"]


def snapshot(sample_seconds: float) -> list[Proc]:
    """Every process, with cpu set to what it used over sample_seconds."""
    before = _cpu_seconds()
    time.sleep(sample_seconds)
    procs = []
    for process in psutil.process_iter(_ATTRS + ["cpu_times"]):
        info = process.info
        if info["memory_info"] is None:
            continue
        cpu = _total(info["cpu_times"])
        procs.append(
            Proc(
                pid=info["pid"],
                ppid=info["ppid"] or 0,
                name=info["name"] or "",
                exe=info["exe"] or "",
                cmdline=info["cmdline"] or [],
                cwd=Path(info["cwd"]) if info["cwd"] else None,
                memory=_memory(info["pid"]) or info["memory_info"].rss,
                started=info["create_time"] or 0.0,
                cpu=max(0.0, cpu - before.get(info["pid"], cpu)),
                username=info["username"] or "",
                container=_container(info["pid"]),
            )
        )
    return procs


def _cpu_seconds() -> dict[int, float]:
    return {p.pid: _total(p.info["cpu_times"]) for p in psutil.process_iter(["cpu_times"])}


def _total(times) -> float:
    return times.user + times.system if times else 0.0


if sys.platform == "darwin":

    class _RusageInfoV0(ctypes.Structure):
        _fields_ = [
            ("uuid", ctypes.c_uint8 * 16),
            ("user_time", ctypes.c_uint64),
            ("system_time", ctypes.c_uint64),
            ("pkg_idle_wkups", ctypes.c_uint64),
            ("interrupt_wkups", ctypes.c_uint64),
            ("pageins", ctypes.c_uint64),
            ("wired_size", ctypes.c_uint64),
            ("resident_size", ctypes.c_uint64),
            ("phys_footprint", ctypes.c_uint64),
            ("proc_start_abstime", ctypes.c_uint64),
            ("proc_exit_abstime", ctypes.c_uint64),
        ]

    _libsystem = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)

    def _memory(pid: int) -> int | None:
        """The process's footprint, as Activity Monitor's Memory column shows it, or None
        when it isn't ours to read."""
        info = _RusageInfoV0()
        if _libsystem.proc_pid_rusage(pid, 0, ctypes.byref(info)) != 0:
            return None
        return info.phys_footprint

    def _container(pid: int) -> str | None:
        return None  # On macOS containers run in a VM, never as host processes.

else:

    def _memory(pid: int) -> int | None:
        """The process's proportional set size: its private memory and its share of what it
        shares, or None when it isn't ours to read."""
        try:
            text = Path(f"/proc/{pid}/smaps_rollup").read_text()
        except OSError:
            return None
        match = re.search(r"^Pss:\s+(\d+) kB", text, flags=re.M)
        return int(match[1]) * 1024 if match else None

    def _container(pid: int) -> str | None:
        try:
            text = Path(f"/proc/{pid}/cgroup").read_text()
        except OSError:
            return None
        return container_id(text)


def container_id(cgroup: str) -> str | None:
    """The Docker container a Linux process runs in, from its /proc/<pid>/cgroup."""
    match = re.search(r"docker[-/]([0-9a-f]{64})", cgroup)
    return match[1] if match else None
