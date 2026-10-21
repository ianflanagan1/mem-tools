"""Sizes and durations as people read them, and durations as people type them."""

import re


def size(count: int) -> str:
    """Bytes in the largest unit that keeps a whole number in front: 512 B, 340 MB, 1.2 GB.

    Units are powers of 1024, labelled as Activity Monitor and free(1) label them.
    """
    for unit, power in (("GB", 3), ("MB", 2), ("KB", 1)):
        if count >= 1024**power:
            value = count / 1024**power
            return f"{value:.1f} {unit}" if value < 10 else f"{value:.0f} {unit}"
    return f"{count} B"


def duration(seconds: float) -> str:
    """Seconds as the largest whole unit: 45s, 12m, 5h, 3d."""
    for unit, length in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= length:
            return f"{int(seconds // length)}{unit}"
    return f"{int(seconds)}s"


def parse_duration(text: str) -> float:
    """Seconds from a duration such as 90s, 30m, 2h or 1d. Raises ValueError otherwise."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([smhd])", text.strip())
    if not match:
        raise ValueError(f"not a duration such as 30m, 2h or 1d: {text}")
    return float(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]
