"""Grouping processes into items: the things you'd stop as one.

Every process from one macOS app bundle is one item, as a browser's or editor's helpers are,
and a process running its parent's executable, as those helpers do on Linux, joins its parent's.
Otherwise a process starts an item of its own. Two kinds are recognised first, and claim everything
started under them: a Claude Code session, with its shells and MCP servers, and the VM that
runs containers, with the processes that serve it, such as Colima's.
"""

import re
from pathlib import Path

from mem import claude
from mem.claude import Session
from mem.model import Item, Proc

CLAUDE_APP = "Claude Code"
VM_APP = "Container VM"

_BUNDLE = re.compile(r"^(.*?\.app)/")
VM_KEY = "\0vm"


def items(
    procs: list[Proc],
    sessions: dict[int, Session],
    sample_seconds: float,
    vm_stop: str | None = None,
) -> list[Item]:
    """The items procs make. A process in a container is left out: docker counts it.

    vm_stop: the command that stops the container VM, when it's known which runs it.
    """
    by_pid = {p.pid: p for p in procs if p.container is None}
    children: dict[int, list[Proc]] = {}
    for proc in by_pid.values():
        if proc.ppid in by_pid and proc.ppid != proc.pid:
            children.setdefault(proc.ppid, []).append(proc)
    roots = [p for p in by_pid.values() if p.ppid not in by_pid or p.ppid == p.pid]

    result: list[Item] = []
    # Items every process of one program joins wherever it sits in the tree: one per app
    # bundle, and one for the container VM and its helpers.
    shared: dict[str, Item] = {}
    stack = [(root, None) for root in roots]
    while stack:
        proc, parent_item = stack.pop()
        item = _claude(proc, sessions.get(proc.pid)) if _is_claude(proc, sessions) else None
        if item is None and parent_item is not None and parent_item.kind in ("claude", "vm"):
            item = parent_item
        if item is None and (key := _shared_key(proc)):
            if key not in shared:
                shared[key] = _shared_item(key, vm_stop)
            item = shared[key]
        if item is None and parent_item is not None and _same_program(proc, by_pid[proc.ppid]):
            item = parent_item
        if item is None:
            item = _plain(proc)
        if not item.pids:
            result.append(item)
        item.memory += proc.memory
        item.pids.append(proc.pid)
        item.cpu += proc.cpu / sample_seconds if sample_seconds else 0.0
        stack.extend((child, item) for child in children.get(proc.pid, []))
    return result


def _is_claude(proc: Proc, sessions: dict[int, Session]) -> bool:
    return proc.pid in sessions or claude.is_claude(proc)


def _shared_key(proc: Proc) -> str | None:
    if _is_vm(proc) or _is_vm_helper(proc):
        return VM_KEY
    bundle = _BUNDLE.match(proc.exe)
    return bundle[1] if bundle else None


def _shared_item(key: str, vm_stop: str | None) -> Item:
    if key == VM_KEY:
        return Item(
            kind="vm",
            app=VM_APP,
            name={"colima stop": "Colima"}.get(vm_stop or "", "VM"),
            stop=vm_stop,
            note="Stopping containers frees memory inside the VM, not for the host.",
        )
    name = Path(key).stem
    return Item(kind="app", app=name, name=name)


def _claude(proc: Proc, session: Session | None) -> Item:
    if session is None:
        return Item(
            kind="claude",
            app=CLAUDE_APP,
            name=f"pid {proc.pid}",
            cwd=proc.cwd,
            started=proc.started,
            stop=f"kill {proc.pid}",
        )
    note = None
    if session.session_id:
        note = f"resume: cd {session.cwd} && claude --resume {session.session_id}"
    return Item(
        kind="claude",
        app=CLAUDE_APP,
        name=session.name or f"pid {proc.pid}",
        cwd=session.cwd or proc.cwd,
        started=proc.started,
        idle_since=None if session.busy else session.last_active,
        stop=f"kill {proc.pid}",
        note=note,
    )


def _is_vm(proc: Proc) -> bool:
    return proc.name == "com.apple.Virtualization.VirtualMachine" or proc.name.startswith(
        "qemu-system"
    )


def _is_vm_helper(proc: Proc) -> bool:
    """A process that runs the VM's networking or ports for it, such as Colima's limactl."""
    command = " ".join(proc.cmdline)
    return proc.name in ("limactl", "colima") or (
        proc.name == "ssh" and ("/.colima/" in command or "/.lima/" in command)
    )


def _plain(proc: Proc) -> Item:
    name = proc.name or Path(proc.exe).name
    return Item(
        kind="process",
        app=name,
        name=name,
        cwd=proc.cwd,
        started=proc.started,
        stop=f"kill {proc.pid}",
    )


def _same_program(proc: Proc, parent: Proc) -> bool:
    """Whether proc is a helper of parent: the same executable, as a browser's are on Linux."""
    return bool(proc.exe) and proc.exe == parent.exe
