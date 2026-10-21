"""mem projects [<filter>]

Lists what's using memory by project: each repo under the projects root, then each of its
worktrees, with the Claude Code sessions working there, the compose projects started there and
any other process running there. Sessions and containers outside every project are listed
under "other". The root is ~/projects, or MEM_PROJECTS when that's set.

Name a project (any part of it, ignoring case) to see inside it, down to each session and each
container. On macOS containers run in a VM, so their memory is inside the VM's, not extra.
"""

import time

from cli_kit import cli
from cli_kit.colour import Style
from cli_kit.outcome import NothingToDo, Precondition

from mem import render, survey
from mem.commands import headroom, options
from mem.projects import Locator


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "projects",
        help="list memory use by project and worktree; name one to see inside it",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("filter", nargs="?", help="show only projects whose name contains this")
    parser.add_argument(
        "--depth", type=int, metavar="levels", help="levels to show (default 2, or 4 with filter)"
    )
    options.add(parser, idle=False)
    parser.set_defaults(run=lambda args: projects(args.filter, args.depth, args.sample))


def projects(filter: str | None, depth: int | None, sample: float) -> NothingToDo:
    found = survey.take(sample)
    nodes = render.by_project(found.items, Locator(survey.projects_root()), time.time())
    if filter:
        nodes = render.matching(nodes, filter)
        if not nodes:
            raise Precondition(f"No project's name contains {filter!r}.")
    if not found.docker_running:
        print("Docker isn't answering, so containers aren't listed.")
    colour = Style.for_stream()
    print("\n".join(render.lines(nodes, depth or (4 if filter else 2), colour)))
    print()
    return NothingToDo(headroom.summary(found.headroom))
