"""The views of a survey as trees, and trees as indented lines with a column of sizes.

By app: each app, then its items, then their parts. By project: each project, then its
worktrees when it has more than one, then the items working in them, then their parts. Depth
says how many levels to show.
"""

from collections import Counter
from dataclasses import dataclass, field

from cli_kit.colour import BOLD, GREY, Style

from mem import docker
from mem.model import Item
from mem.projects import Locator
from mem.units import duration, size

OTHER = "other"

# Items placed under "other" in the projects view; any other item outside a project is only
# listed by app.
_PLACED_ANYWHERE = ("claude", "compose", "container")


@dataclass
class Node:
    label: str
    memory: int
    note: str = ""
    children: list["Node"] = field(default_factory=list)


def by_app(items: list[Item], now: float) -> list[Node]:
    apps: dict[str, list[Item]] = {}
    for item in items:
        apps.setdefault(item.app, []).append(item)
    nodes = []
    for app, members in apps.items():
        count = sum(len(i.pids) for i in members)
        note = f"{count} process{'es' if count != 1 else ''}"
        if app == docker.APP:
            count = sum(len(i.parts) for i in members)
            note = f"{count} container{'s' if count != 1 else ''}"
        if len(members) > 1:
            note = f"×{len(members)}" + (f" · {note}" if note else "")
        nodes.append(Node(app, sum(i.memory for i in members), note, _items(members, now)))
    return _ranked(nodes)


def by_project(items: list[Item], locator: Locator, now: float) -> list[Node]:
    projects: dict[str, dict[str | None, list[Item]]] = {}
    for item in items:
        place = locator.place(item.cwd) if item.cwd else None
        if place is None and item.kind not in _PLACED_ANYWHERE:
            continue
        project, worktree = (place.project, place.worktree) if place else (OTHER, None)
        projects.setdefault(project, {}).setdefault(worktree, []).append(item)
    nodes = []
    for project, worktrees in projects.items():
        members = [i for group in worktrees.values() for i in group]
        named = [w for w in worktrees if w is not None]
        if len(worktrees) == 1:  # one worktree, or none: its items directly under the project
            children = _items(members, now)
        else:
            children = [
                Node(
                    w,
                    sum(i.memory for i in worktrees[w]),
                    _kinds(worktrees[w], now),
                    _items(worktrees[w], now),
                )
                for w in named
            ]
            children += _items(worktrees.get(None, []), now)
        nodes.append(
            Node(project, sum(i.memory for i in members), _kinds(members, now), _ranked(children))
        )
    return sorted(_ranked(nodes), key=lambda node: node.label == OTHER)


def describe(item: Item, now: float) -> str:
    """What an item's line says after its name: idle time, pids, where it is, what's in it."""
    notes = []
    if item.kind == "claude":
        notes.append(
            "busy" if item.idle_since is None else f"idle {duration(now - item.idle_since)}"
        )
    if item.kind in ("compose", "container"):
        count = len(item.parts)
        notes.append(f"{count} container{'s' if count != 1 else ''}")
    elif item.pids:
        notes.append(
            f"pid {item.pids[0]}" + (f" +{len(item.pids) - 1}" if len(item.pids) > 1 else "")
        )
    if item.in_vm:
        notes.append("in VM")
    return " · ".join(notes)


def lines(nodes: list[Node], depth: int, colour: Style, width: int = 34) -> list[str]:
    """The tree to depth levels. A node with hidden children shows the count it hides."""
    out = []

    def walk(node: Node, level: int) -> None:
        label = "  " * level + node.label
        if len(label) > width:
            label = label[: width - 1] + "…"
        note = node.note
        if node.children and level + 1 >= depth:
            note = note or f"{len(node.children)} more"
        label = f"{label:<{width}}"
        if level == 0:
            label = colour(BOLD, label)
        out.append(f"{label} {size(node.memory):>7}  {colour(GREY, note)}".rstrip())
        if level + 1 < depth:
            for child in node.children:
                walk(child, level + 1)

    for node in nodes:
        walk(node, 0)
    return out


def matching(nodes: list[Node], text: str) -> list[Node]:
    """The top-level nodes whose label contains text, ignoring case."""
    return [node for node in nodes if text.lower() in node.label.lower()]


def _items(items: list[Item], now: float) -> list[Node]:
    return _ranked(
        [
            Node(
                item.name,
                item.memory,
                describe(item, now),
                [Node(part.name, part.memory) for part in item.parts],
            )
            for item in items
        ]
    )


def _kinds(items: list[Item], now: float) -> str:
    """A summary such as "claude ×9 (7 idle) · compose ×1"."""
    counts = Counter(_kind_name(item) for item in items)
    idle = sum(1 for i in items if i.kind == "claude" and i.idle_since is not None)
    parts = []
    for kind, count in counts.most_common():
        text = kind if count == 1 else f"{kind} ×{count}"
        if kind == "claude" and idle:
            text += f" ({idle} idle)"
        parts.append(text)
    return " · ".join(parts)


def _kind_name(item: Item) -> str:
    if item.kind in ("claude", "compose", "container"):
        return item.kind
    return item.app


def _ranked(nodes: list[Node]) -> list[Node]:
    return sorted(nodes, key=lambda node: -node.memory)
