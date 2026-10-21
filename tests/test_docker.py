from datetime import UTC, datetime
from pathlib import Path

from mem.docker import items, parse, size


def inspected(id: str, name: str, project: str | None = None, service: str | None = None) -> dict:
    labels = {}
    if project:
        labels = {
            "com.docker.compose.project": project,
            "com.docker.compose.service": service,
            "com.docker.compose.project.working_dir": f"/p/{project}",
        }
    return {
        "Id": id,
        "Name": f"/{name}",
        "Config": {"Labels": labels},
        "State": {"StartedAt": "2026-10-12T17:47:31.123456789Z"},
    }


def stats(id: str, memory: str, cpu: str = "0.50%") -> dict:
    return {"Container": id, "MemUsage": f"{memory} / 1.913GiB", "CPUPerc": cpu}


def test_a_container_is_read_from_inspect_and_stats():
    [c] = parse([inspected("a1", "app-db-1", "app", "db")], [stats("a1", "43.5MiB", "1.50%")])
    assert (c.name, c.project, c.service, c.working_dir) == (
        "app-db-1",
        "app",
        "db",
        Path("/p/app"),
    )
    assert (c.memory, c.cpu) == (int(43.5 * 2**20), 0.015)
    assert c.started == datetime(2026, 10, 12, 17, 47, 31, 123456, UTC).timestamp()


def test_containers_of_one_compose_project_are_one_item_with_a_part_each():
    found = parse(
        [inspected("a1", "app-db-1", "app", "db"), inspected("a2", "app-web-1", "app", "web")],
        [stats("a1", "40MiB"), stats("a2", "10MiB")],
    )
    [item] = items(found, in_vm=True)
    assert (item.kind, item.name, item.cwd, item.in_vm) == ("compose", "app", Path("/p/app"), True)
    assert item.memory == 50 * 2**20
    assert [p.name for p in item.parts] == ["db", "web"]
    assert item.stop == "docker compose -p app stop"


def test_a_container_started_without_compose_is_its_own_item():
    found = parse([inspected("b1", "scratch"), inspected("b2", "other")], [])
    assert [(i.kind, i.name, i.stop) for i in items(found, in_vm=False)] == [
        ("container", "scratch", "docker stop scratch"),
        ("container", "other", "docker stop other"),
    ]


def test_sizes_are_read_in_dockers_binary_and_decimal_units():
    assert [size(s) for s in ["512B", "1.5KiB", "2MiB", "1GiB", "1kB", "3MB", "1GB", "?"]] == [
        512,
        1536,
        2 * 2**20,
        2**30,
        1000,
        3 * 10**6,
        10**9,
        0,
    ]
