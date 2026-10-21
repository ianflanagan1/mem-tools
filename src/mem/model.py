"""What a survey of memory is made of: processes, and the items they're grouped into."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Proc:
    """One process, as the snapshot saw it.

    memory: bytes it holds that would be freed by stopping it, as near as the OS says: the
    footprint on macOS, PSS on Linux, else RSS. cpu: CPU seconds it used during the sample.
    container: on Linux, the Docker container it runs in, whose memory docker counts instead.
    """

    pid: int
    ppid: int
    name: str
    exe: str
    cmdline: list[str]
    cwd: Path | None
    memory: int
    started: float
    cpu: float = 0.0
    username: str = ""
    container: str | None = None


@dataclass
class Part:
    """A line inside an item, shown when it's expanded: a container of a compose project, or
    a process of a session."""

    name: str
    memory: int


@dataclass
class Item:
    """Something you could stop as one: an app, a Claude session, a compose project, a VM.

    app: the group it's listed under in `mem apps`, such as "Brave Browser" or "Claude Code".
    name: this one among them, such as a session's name. cwd: where it works, which places it
    under a project. idle_since: when it was last active, when that's known. stop: the command
    that stops it. in_vm: its memory is inside the container VM, so stopping it frees memory for
    other containers but doesn't give it back to the host.
    """

    kind: str
    app: str
    name: str
    memory: int = 0
    pids: list[int] = field(default_factory=list)
    cwd: Path | None = None
    started: float | None = None
    cpu: float = 0.0
    idle_since: float | None = None
    stop: str | None = None
    note: str | None = None
    in_vm: bool = False
    parts: list[Part] = field(default_factory=list)
