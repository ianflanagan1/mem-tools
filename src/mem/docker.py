"""Docker containers, grouped by the compose project that started them.

Compose labels each container with its project and the directory it was started from, which
places the project under a worktree. Memory is what `docker stats` reports for each container's
cgroup. Containers started without compose are each their own item.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mem.model import Item, Part

APP = "Docker containers"

_UNITS = {"B": 1, "KIB": 2**10, "MIB": 2**20, "GIB": 2**30, "TIB": 2**40}
_UNITS |= {"KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}


@dataclass
class Container:
    id: str
    name: str
    project: str | None
    service: str | None
    working_dir: Path | None
    memory: int
    cpu: float
    started: float | None


def containers() -> list[Container] | None:
    """The running containers, or None when docker isn't installed or its daemon isn't up."""
    ids = _docker("ps", "-q", "--no-trunc")
    if ids is None:
        return None
    if not ids.strip():
        return []
    inspected = _docker("inspect", *ids.split())
    stats = _docker("stats", "--no-stream", "--no-trunc", "--format", "{{json .}}")
    if inspected is None or stats is None:
        return None
    return parse(json.loads(inspected), [json.loads(line) for line in stats.splitlines() if line])


def parse(inspected: list[dict], stats: list[dict]) -> list[Container]:
    """Containers from `docker inspect`'s output and the lines of
    `docker stats --format '{{json .}}'`."""
    usage = {row["Container"]: row for row in stats}
    found = []
    for record in inspected:
        labels = record.get("Config", {}).get("Labels") or {}
        row = usage.get(record["Id"], {})
        working_dir = labels.get("com.docker.compose.project.working_dir")
        found.append(
            Container(
                id=record["Id"],
                name=record.get("Name", "").lstrip("/"),
                project=labels.get("com.docker.compose.project"),
                service=labels.get("com.docker.compose.service"),
                working_dir=Path(working_dir) if working_dir else None,
                memory=size(row.get("MemUsage", "0B").split("/")[0]),
                cpu=float(row.get("CPUPerc", "0%").rstrip("%") or 0) / 100,
                started=_timestamp(record.get("State", {}).get("StartedAt")),
            )
        )
    return found


def items(found: list[Container], in_vm: bool) -> list[Item]:
    """One item per compose project, and one per container started without compose."""
    projects: dict[str, list[Container]] = {}
    for container in found:
        projects.setdefault(container.project or f"\0{container.id}", []).append(container)
    result = []
    for key, members in projects.items():
        first = members[0]
        compose = not key.startswith("\0")
        starts = [c.started for c in members if c.started]
        result.append(
            Item(
                kind="compose" if compose else "container",
                app=APP,
                name=key if compose else first.name,
                memory=sum(c.memory for c in members),
                cwd=first.working_dir,
                started=min(starts) if starts else None,
                cpu=sum(c.cpu for c in members),
                stop=f"docker compose -p {key} stop" if compose else f"docker stop {first.name}",
                in_vm=in_vm,
                parts=[Part(c.service or c.name, c.memory) for c in members],
            )
        )
    return result


def size(text: str) -> int:
    """Bytes from a size docker prints, such as 43.39MiB or 1.2GB."""
    match = re.fullmatch(r"\s*([\d.]+)\s*([A-Za-z]*)\s*", text)
    if not match:
        return 0
    return int(float(match[1]) * _UNITS.get(match[2].upper() or "B", 1))


def _timestamp(text: str | None) -> float | None:
    """Seconds since the epoch from docker's time, which has nanoseconds; None when unset."""
    if not text or text.startswith("0001-"):
        return None
    text = re.sub(r"(\.\d{6})\d+", r"\1", text).replace("Z", "+00:00")
    return datetime.fromisoformat(text).timestamp()


def _docker(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["docker", *args], capture_output=True, text=True, check=False, timeout=30
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None
