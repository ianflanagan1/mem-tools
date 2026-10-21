from mem.system import CRITICAL, NORMAL, WARNING, compressed_bytes, headroom, linux_level


def psi(some: float, full: float) -> str:
    return (
        f"some avg10=0.00 avg60={some:.2f} avg300=0.00 total=1\n"
        f"full avg10=0.00 avg60={full:.2f} avg300=0.00 total=1\n"
    )


def test_linux_pressure_is_normal_when_tasks_rarely_wait_for_memory():
    assert linux_level(psi(2.0, 0.5), 0.01) == NORMAL


def test_linux_pressure_is_a_warning_when_some_task_often_waits_for_memory():
    assert linux_level(psi(12.0, 1.0), 0.5) == WARNING


def test_linux_pressure_is_critical_when_every_task_often_stalls_at_once():
    assert linux_level(psi(40.0, 6.0), 0.5) == CRITICAL


def test_without_pressure_information_the_level_comes_from_memory_available():
    assert [linux_level(None, share) for share in (0.5, 0.1, 0.02)] == [NORMAL, WARNING, CRITICAL]


def test_compressed_memory_is_read_from_vm_stat():
    text = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                               12345.\n"
        "Pages occupied by compressor:              1000.\n"
    )
    assert compressed_bytes(text) == 16_384_000


def test_this_machines_headroom_is_read():
    room = headroom()
    assert room.level in (NORMAL, WARNING, CRITICAL)
    assert 0 < room.available <= room.total
