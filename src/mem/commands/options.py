"""The options every view shares: how long to sample CPU for, and how long idle counts."""

import argparse

from mem.units import parse_duration

DEFAULT_SAMPLE = 1.0
DEFAULT_IDLE = "1h"


def add(parser: argparse.ArgumentParser, idle: bool = True) -> None:
    """Adds --sample, and --idle when the command judges what's idle."""
    parser.add_argument(
        "--sample",
        type=float,
        default=DEFAULT_SAMPLE,
        metavar="seconds",
        help=f"how long to watch CPU use, to tell idle from busy (default {DEFAULT_SAMPLE:g})",
    )
    if not idle:
        return
    parser.add_argument(
        "--idle",
        type=_duration,
        default=parse_duration(DEFAULT_IDLE),
        metavar="duration",
        help=f"how long unused counts as idle, such as 30m, 2h or 1d (default {DEFAULT_IDLE})",
    )


def _duration(text: str) -> float:
    try:
        return parse_duration(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from None
