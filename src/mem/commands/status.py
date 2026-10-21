"""mem status

How close the machine is to running out of memory, the apps and projects using the most, and
how much the suggestions would free. Run with no command, mem does this.
"""

import time

from cli_kit import cli
from cli_kit.colour import GREEN, RED, YELLOW, Style
from cli_kit.outcome import NothingToDo

from mem import render, survey
from mem.commands import headroom, options
from mem.projects import Locator
from mem.suggest import suggestions
from mem.system import CRITICAL, WARNING
from mem.units import size

TOP = 5


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "status",
        help="how close to the limit, the biggest users, and what could be freed",
        description=__doc__.split("\n\n", 1)[1],
    )
    options.add(parser)
    parser.set_defaults(run=lambda args: status(args.sample, args.idle))


def status(sample: float, idle: float) -> NothingToDo:
    found = survey.take(sample)
    now = time.time()
    locator = Locator(survey.projects_root())
    colour = Style.for_stream()
    sections = {
        "Top apps": render.by_app(found.items, now),
        "Top projects": render.by_project(found.items, locator, now),
    }
    print(
        "\n\n".join(
            "\n".join([heading, *render.lines(nodes[:TOP], 1, colour)])
            for heading, nodes in sections.items()
            if nodes
        )
    )
    ranked = suggestions(found, locator, now, idle)
    if ranked:
        host = sum(s.item.memory for s in ranked if not s.item.in_vm)
        print(f"\n{len(ranked)} suggestions, freeing up to {size(host)}: run `mem suggest`.")
    print()
    level_colour = {WARNING: YELLOW, CRITICAL: RED}.get(found.headroom.level, GREEN)
    return NothingToDo(colour(level_colour, headroom.summary(found.headroom)))
