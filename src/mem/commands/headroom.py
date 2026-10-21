"""The headroom line every view ends with."""

from mem.system import Headroom
from mem.units import size


def summary(headroom: Headroom) -> str:
    """Such as "Memory pressure normal: 21 GB available of 48 GB, no swap in use."."""
    swap = f"{size(headroom.swap_used)} swapped" if headroom.swap_used else "no swap in use"
    compressed = f", {size(headroom.compressed)} compressed" if headroom.compressed else ""
    return (
        f"Memory pressure {headroom.level}: {size(headroom.available)} available"
        f" of {size(headroom.total)}{compressed}, {swap}."
    )
