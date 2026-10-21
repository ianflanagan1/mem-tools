"""mem suggest

Lists what's worth stopping to free memory, with why and the command that stops it. It runs
nothing itself.

- "likely": a Claude Code session idle for longer than --idle. Its transcript is kept, so the
  resume line brings it back. A session in VS Code also ends when you close its tab.
- "maybe": a compose project whose containers used no CPU during the sample, in a worktree with
  no Claude session active within --idle. You may be working there without Claude.
- the container VM, when no containers are running, or all of them are suggested. On macOS
  stopping containers frees memory only inside the VM; stopping the VM gives it back.

Never suggests the Claude session that ran it.
"""

import time

from cli_kit import cli
from cli_kit.colour import BOLD, GREY, Style
from cli_kit.outcome import NothingToDo

from mem import survey
from mem.commands import headroom, options
from mem.projects import Locator
from mem.suggest import LIKELY, suggestions
from mem.units import size


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "suggest",
        help="list what's worth stopping, why, and the command that stops it",
        description=__doc__.split("\n\n", 1)[1],
    )
    options.add(parser)
    parser.set_defaults(run=lambda args: suggest(args.sample, args.idle))


def suggest(sample: float, idle: float) -> NothingToDo:
    found = survey.take(sample)
    ranked = suggestions(found, Locator(survey.projects_root()), time.time(), idle)
    if not ranked:
        return NothingToDo(f"Nothing worth stopping. {headroom.summary(found.headroom)}")
    colour = Style.for_stream()
    for suggestion in ranked:
        item = suggestion.item
        title = f"{suggestion.confidence:<6} {item.app} · {item.name}"
        print(f"{colour(BOLD, f'{title:<48}')} {size(item.memory):>7}  {suggestion.reason}")
        if item.in_vm:
            print(colour(GREY, "       frees memory inside the VM, not for the host"))
        if item.stop:
            print(f"       {item.stop}")
        if item.note:
            print(colour(GREY, f"       {item.note}"))
    kills = [s.item.stop for s in ranked if s.confidence == LIKELY and s.item.kind == "claude"]
    if len(kills) > 1:
        pids = " ".join(stop.removeprefix("kill ") for stop in kills)
        print(f"\nEvery likely Claude session at once:\n       kill {pids}")
    print()
    host = sum(s.item.memory for s in ranked if not s.item.in_vm)
    return NothingToDo(
        f"{len(ranked)} suggestion{'s' if len(ranked) != 1 else ''}, freeing up to"
        f" {size(host)} for the host. {headroom.summary(found.headroom)}"
    )
