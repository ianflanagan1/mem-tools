from pathlib import Path

from mem.model import Item, Part
from mem.projects import Locator
from mem.suggest import LIKELY, MAYBE, suggestions
from mem.survey import Survey
from mem.system import Headroom

NOW = 100_000.0
HOUR = 3600.0


def survey(*items: Item, docker_running: bool = True, own: set[int] = frozenset()) -> Survey:
    return Survey(Headroom("normal", 0, 0, 0), list(items), docker_running, set(own))


def session(pid: int, idle_for: float | None, cwd: str = "/root/app", memory: int = 100) -> Item:
    idle_since = None if idle_for is None else NOW - idle_for
    return Item("claude", "Claude Code", f"s{pid}", memory, [pid], Path(cwd), idle_since=idle_since)


def stack(cwd: str = "/root/app", cpu: float = 0.0, containers: int = 2) -> Item:
    parts = [Part(f"c{n}", 10) for n in range(containers)]
    return Item(
        "compose", "Docker containers", "app", 20, [], Path(cwd), cpu=cpu, in_vm=True, parts=parts
    )


def vm() -> Item:
    return Item("vm", "Container VM", "Colima", 1000, [5], stop="colima stop")


def found(s: Survey) -> list[tuple[str, str]]:
    return [(x.item.name, x.confidence) for x in suggestions(s, Locator(Path("/root")), NOW, HOUR)]


def test_a_claude_session_idle_longer_than_the_threshold_is_likely_worth_stopping():
    assert found(survey(session(1, 2 * HOUR), session(2, HOUR / 2))) == [("s1", LIKELY)]


def test_a_busy_claude_session_is_never_suggested():
    assert found(survey(session(1, None))) == []


def test_the_claude_session_that_ran_mem_is_never_suggested():
    assert found(survey(session(1, 2 * HOUR), own={1, 99})) == []


def test_idle_containers_with_no_active_session_in_their_project_may_be_worth_stopping():
    assert found(survey(stack(), session(1, 2 * HOUR, cwd="/root/app"))) == [
        ("s1", LIKELY),
        ("app", MAYBE),
    ]


def test_containers_in_a_project_with_an_active_session_are_not_suggested():
    assert found(survey(stack(), session(1, None, cwd="/root/app"))) == []


def test_containers_busy_during_the_sample_are_not_suggested():
    assert found(survey(stack(cpu=0.5))) == []


def test_containers_idle_threshold_allows_each_container_a_little_background_cpu():
    assert found(survey(stack(cpu=0.08, containers=2))) == [("app", MAYBE)]


def test_the_vm_is_likely_worth_stopping_when_no_containers_run():
    assert found(survey(vm())) == [("Colima", LIKELY)]


def test_the_vm_may_be_worth_stopping_when_every_container_is_suggested():
    assert found(survey(vm(), stack())) == [("Colima", MAYBE), ("app", MAYBE)]


def test_the_vm_is_not_suggested_while_some_container_is_in_use():
    assert found(survey(vm(), stack(cpu=0.5))) == []


def test_the_vm_may_be_worth_stopping_when_docker_doesnt_answer():
    assert found(survey(vm(), docker_running=False)) == [("Colima", MAYBE)]


def test_likely_suggestions_come_before_maybes_then_the_largest_first():
    s = survey(stack(), session(1, 2 * HOUR, "/x", 50), session(2, 2 * HOUR, "/x", 80))
    assert found(s) == [("s2", LIKELY), ("s1", LIKELY), ("app", MAYBE)]
