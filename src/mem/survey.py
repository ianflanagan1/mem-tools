"""One look at the machine: its headroom, and every item using memory."""

import os
from dataclasses import dataclass
from pathlib import Path

import psutil

from mem import claude, docker, grouping, processes, system
from mem.model import Item, Proc
from mem.system import Headroom


@dataclass
class Survey:
    headroom: Headroom
    items: list[Item]
    docker_running: bool
    # This command and the processes that started it, such as the Claude session that ran it,
    # which are never suggested for stopping.
    own_pids: set[int]


def take(sample_seconds: float) -> Survey:
    procs = processes.snapshot(sample_seconds)
    sessions = claude.sessions(claude.config_dir())
    items = grouping.items(procs, sessions, sample_seconds, vm_stop(procs))
    containers = docker.containers()
    if containers:
        items += docker.items(containers, in_vm=any(item.kind == "vm" for item in items))
    return Survey(system.headroom(), items, containers is not None, _ancestors())


def vm_stop(procs: list[Proc]) -> str | None:
    """The command that stops the container VM, when it's one we know how to stop."""
    for proc in procs:
        command = " ".join(proc.cmdline)
        if "limactl" in command and "/.colima/" in command:
            return "colima stop"
        if proc.name == "com.docker.backend":
            return "quit Docker Desktop"
    return None


def _ancestors() -> set[int]:
    pids = set()
    process: psutil.Process | None = psutil.Process(os.getpid())
    while process is not None and process.pid not in pids:
        pids.add(process.pid)
        try:
            process = process.parent()
        except psutil.Error:
            break
    return pids


def projects_root() -> Path:
    return Path(os.environ.get("MEM_PROJECTS") or Path.home() / "projects")
