import pytest

from mem.units import duration, parse_duration, size


def test_sizes_show_one_decimal_below_ten_and_none_above():
    assert [size(n) for n in (512, 2048, 1536 * 2**20, 30 * 2**30)] == [
        "512 B",
        "2.0 KB",
        "1.5 GB",
        "30 GB",
    ]


def test_durations_show_the_largest_whole_unit():
    assert [duration(s) for s in (45, 750, 5 * 3600 + 59, 3 * 86400)] == ["45s", "12m", "5h", "3d"]


def test_durations_are_typed_with_a_unit():
    assert [parse_duration(t) for t in ("90s", "30m", "2h", "1.5d")] == [90, 1800, 7200, 129600]


def test_a_duration_without_a_unit_is_refused():
    with pytest.raises(ValueError):
        parse_duration("2")
