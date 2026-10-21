"""mem apps [<filter>]

Lists what's using memory by app: all of a browser's or editor's helper processes as one line,
each Claude Code session's shells and MCP servers with it, and Docker's containers. Apps under
50 MB are summed into one line unless you pass --all.

Name an app (any part of it, ignoring case) to see inside it: its items, such as each Claude
session with its idle time, and theirs, such as each container of a compose project.
"""

import time

from cli_kit import cli
from cli_kit.colour import Style
from cli_kit.outcome import NothingToDo, Precondition

from mem import render, survey
from mem.commands import headroom, options
from mem.units import size

SMALL = 50 * 2**20


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "apps",
        help="list memory use by app; name one to see inside it",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("filter", nargs="?", help="show only apps whose name contains this")
    parser.add_argument(
        "--depth", type=int, metavar="levels", help="levels to show (default 1, or 3 with filter)"
    )
    parser.add_argument("--all", action="store_true", help="list small apps one by one too")
    options.add(parser, idle=False)
    parser.set_defaults(run=lambda args: apps(args.filter, args.depth, args.all, args.sample))


def apps(filter: str | None, depth: int | None, everything: bool, sample: float) -> NothingToDo:
    found = survey.take(sample)
    nodes = render.by_app(found.items, time.time())
    small = []
    if filter:
        nodes = render.matching(nodes, filter)
        if not nodes:
            raise Precondition(f"No app's name contains {filter!r}.")
    elif not everything:
        small = [node for node in nodes if node.memory < SMALL]
        nodes = nodes[: len(nodes) - len(small)]
    colour = Style.for_stream()
    print("\n".join(render.lines(nodes, depth or (3 if filter else 1), colour)))
    if small:
        print(f"{len(small)} more under {size(SMALL)}, {size(sum(n.memory for n in small))} in all")
    print()
    return NothingToDo(headroom.summary(found.headroom))
