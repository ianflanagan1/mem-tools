"""`mem <command> ...`: how close the machine is to running out of memory, what's using it, and
what's safe to stop. With no command, `mem status`."""

import sys

from cli_kit import cli

from mem.commands import apps, projects, status, suggest

COMMANDS = [status, apps, projects, suggest]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    return cli.run(
        "mem",
        "How close this machine is to running out of memory, what's using it, and what's safe"
        " to stop.",
        COMMANDS,
        argv or ["status"],
    )


if __name__ == "__main__":
    sys.exit(main())
