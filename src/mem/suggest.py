"""What's worth stopping, and why.

Only what mem can tell is unused is suggested:

- a Claude Code session idle for longer than the threshold. Its transcript is kept, so it can be
  resumed later;
- a compose project whose containers used no CPU during the sample, in a worktree with no Claude
  session active within the threshold. That is a guess, so it's marked as one;
- the container VM, when no containers are running, or every running one is suggested.
"""

from dataclasses import dataclass

from mem.model import Item
from mem.projects import Locator
from mem.survey import Survey
from mem.units import duration

LIKELY, MAYBE = "likely", "maybe"

# Below this share of one core each, on average during the sample, containers count as idle.
# Databases and caches use a little even when nothing asks them anything.
IDLE_CPU = 0.05


@dataclass
class Suggestion:
    item: Item
    reason: str
    confidence: str


def suggestions(survey: Survey, locator: Locator, now: float, idle: float) -> list[Suggestion]:
    """Ranked: likely before maybe, then by memory, largest first."""
    found = []
    sessions = [i for i in survey.items if i.kind == "claude"]
    for item in sessions:
        if survey.own_pids & set(item.pids) or item.idle_since is None:
            continue
        if now - item.idle_since >= idle:
            found.append(Suggestion(item, f"idle {duration(now - item.idle_since)}", LIKELY))

    active = {
        locator.place(s.cwd)
        for s in sessions
        if s.cwd and (s.idle_since is None or now - s.idle_since < idle)
    }
    stacks = [i for i in survey.items if i.kind in ("compose", "container")]
    for item in stacks:
        place = locator.place(item.cwd) if item.cwd else None
        if item.cpu < IDLE_CPU * max(1, len(item.parts)) and (place is None or place not in active):
            reason = f"containers idle, and no Claude session active here in {duration(idle)}"
            found.append(Suggestion(item, reason, MAYBE))

    suggested = {id(s.item) for s in found}
    for vm in (i for i in survey.items if i.kind == "vm"):
        if not survey.docker_running:
            reason = "docker isn't answering, so nothing can be using its containers"
            found.append(Suggestion(vm, reason, MAYBE))
        elif not stacks:
            found.append(Suggestion(vm, "no containers running", LIKELY))
        elif all(id(item) in suggested for item in stacks):
            found.append(Suggestion(vm, "every running container is suggested too", MAYBE))

    return sorted(found, key=lambda s: (s.confidence != LIKELY, -s.item.memory))
