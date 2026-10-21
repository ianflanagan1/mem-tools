import os
from pathlib import Path

from mem.processes import container_id, snapshot


def test_the_snapshot_includes_this_process_with_its_memory_and_directory():
    me = next(p for p in snapshot(0.1) if p.pid == os.getpid())
    assert me.memory > 0
    assert me.cwd == Path.cwd()
    assert me.ppid == os.getppid()


def test_a_process_in_a_docker_container_is_known_by_its_cgroup():
    cid = "a" * 64
    assert container_id(f"0::/system.slice/docker-{cid}.scope\n") == cid
    assert container_id(f"12:memory:/docker/{cid}\n") == cid
    assert container_id("0::/user.slice/user-1000.slice/session-2.scope\n") is None
