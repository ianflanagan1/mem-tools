from pathlib import Path

from cli_kit.colour import Style

from mem.model import Item, Part
from mem.projects import Locator, Place
from mem.render import OTHER, by_app, by_project, lines, matching

NOW = 10_000.0


class FakeLocator(Locator):
    def __init__(self, places: dict[str, Place]) -> None:
        self.places = places

    def place(self, directory: Path) -> Place | None:
        return self.places.get(str(directory))


def item(kind: str, name: str, memory: int, cwd: str | None = None, **fields) -> Item:
    app = {"claude": "Claude Code", "compose": "Docker containers"}.get(kind, name)
    return Item(kind, app, name, memory, [memory], Path(cwd) if cwd else None, **fields)


def test_apps_are_listed_largest_first_with_their_items_inside():
    nodes = by_app(
        [item("claude", "s1", 10), item("app", "Brave", 50), item("claude", "s2", 30)], NOW
    )
    assert [(n.label, n.memory, [c.label for c in n.children]) for n in nodes] == [
        ("Brave", 50, ["Brave"]),
        ("Claude Code", 40, ["s2", "s1"]),
    ]


def test_a_project_with_one_worktree_lists_its_items_directly():
    locator = FakeLocator({"/p/a": Place("a", "main")})
    [node] = by_project([item("claude", "s1", 10, "/p/a")], locator, NOW)
    assert (node.label, [c.label for c in node.children]) == ("a", ["s1"])


def test_a_project_with_several_worktrees_lists_each_with_its_items():
    locator = FakeLocator({"/p/a": Place("a", "main"), "/p/a-x": Place("a", "x (a-x)")})
    [node] = by_project(
        [
            item("claude", "s1", 10, "/p/a"),
            item("compose", "a-x", 30, "/p/a-x", parts=[Part("db", 30)]),
        ],
        locator,
        NOW,
    )
    assert [(c.label, c.memory, c.note) for c in node.children] == [
        ("x (a-x)", 30, "compose"),
        ("main", 10, "claude"),
    ]


def test_sessions_and_containers_outside_every_project_are_listed_under_other_last():
    locator = FakeLocator({"/p/a": Place("a")})
    nodes = by_project(
        [item("claude", "s1", 99, "/tmp"), item("claude", "s2", 1, "/p/a")], locator, NOW
    )
    assert [n.label for n in nodes] == ["a", OTHER]


def test_other_processes_outside_every_project_are_left_out_of_the_projects_view():
    nodes = by_project([item("process", "zsh", 5, "/Users/me")], FakeLocator({}), NOW)
    assert nodes == []


def test_an_idle_sessions_line_says_how_long_its_been_idle():
    [app] = by_app([item("claude", "s1", 10, idle_since=NOW - 7200)], NOW)
    assert app.children[0].note.startswith("idle 2h")


def test_depth_hides_deeper_levels_and_says_how_many_it_hides():
    nodes = by_app([item("claude", "s1", 10), item("claude", "s2", 30)], NOW)
    [line] = lines(nodes, 1, Style(enabled=False))
    assert line.startswith("Claude Code") and "×2" in line
    assert len(lines(nodes, 2, Style(enabled=False))) == 3


def test_a_long_name_is_cut_to_keep_the_size_column_aligned():
    [line] = lines(by_app([item("app", "x" * 50, 10)], NOW), 1, Style(enabled=False), width=10)
    assert line.startswith("xxxxxxxxx… ")


def test_a_filter_keeps_the_top_level_nodes_whose_name_contains_it_ignoring_case():
    nodes = by_app([item("app", "Brave Browser", 1), item("app", "Finder", 1)], NOW)
    assert [n.label for n in matching(nodes, "brave")] == ["Brave Browser"]
