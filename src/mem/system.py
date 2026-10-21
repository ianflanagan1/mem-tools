"""How close the machine is to running out of memory.

The verdict is the kernel's own where it gives one: on macOS its memory pressure level, which is
what Activity Monitor's pressure graph shows; on Linux the pressure stall information in
/proc/pressure/memory, the share of time tasks waited for memory. Free memory alone misleads on
both, since caches fill what's free and are given up on demand.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

NORMAL, WARNING, CRITICAL = "normal", "warning", "critical"

# macOS's kern.memorystatus_vm_pressure_level.
_MACOS_LEVELS = {1: NORMAL, 2: WARNING, 4: CRITICAL}

# Linux PSI thresholds, as percentages of time over the last minute: some task waiting for
# memory, or all of them stalled at once.
WARNING_SOME = 10.0
CRITICAL_FULL = 5.0

# Without PSI, the share of memory available.
WARNING_AVAILABLE = 0.15
CRITICAL_AVAILABLE = 0.05


@dataclass
class Headroom:
    level: str
    total: int
    available: int
    swap_used: int
    compressed: int | None = None


def headroom() -> Headroom:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory().used
    if sys.platform == "darwin":
        return Headroom(_macos_level(), memory.total, memory.available, swap, _compressed())
    pressure = Path("/proc/pressure/memory")
    text = pressure.read_text() if pressure.exists() else None
    level = linux_level(text, memory.available / memory.total)
    return Headroom(level, memory.total, memory.available, swap)


def linux_level(psi: str | None, available_share: float) -> str:
    """The level from /proc/pressure/memory's text, or from the share available without it."""
    if psi is None:
        if available_share < CRITICAL_AVAILABLE:
            return CRITICAL
        return WARNING if available_share < WARNING_AVAILABLE else NORMAL
    averages = {
        kind: float(avg60)
        for kind, avg60 in re.findall(r"^(some|full) .*?avg60=([\d.]+)", psi, flags=re.M)
    }
    if averages.get("full", 0.0) >= CRITICAL_FULL:
        return CRITICAL
    return WARNING if averages.get("some", 0.0) >= WARNING_SOME else NORMAL


def _macos_level() -> str:
    value = _run("sysctl", "-n", "kern.memorystatus_vm_pressure_level")
    return _MACOS_LEVELS.get(int(value), NORMAL) if value.isdigit() else NORMAL


def _compressed() -> int | None:
    return compressed_bytes(_run("vm_stat"))


def compressed_bytes(vm_stat: str) -> int | None:
    """The memory the compressor holds, from vm_stat's output."""
    page = re.search(r"page size of (\d+) bytes", vm_stat)
    pages = re.search(r"Pages occupied by compressor:\s+(\d+)", vm_stat)
    return int(page[1]) * int(pages[1]) if page and pages else None


def _run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""
