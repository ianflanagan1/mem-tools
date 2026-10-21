from pathlib import Path

from mem.claude import Session
from mem.grouping import CLAUDE_APP, VM_APP, items

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
BRAVE_HELPER = (
    "/Applications/Brave Browser.app/Contents/Frameworks/Brave Browser Framework.framework"
    "/Helpers/Brave Browser Helper (Renderer).app/Contents/MacOS/Brave Browser Helper (Renderer)"
)
CLAUDE = "/Users/me/.vscode/extensions/anthropic.claude-code/resources/native-binary/claude"


def session(pid: int, **fields) -> Session:
    defaults = {
        "session_id": "abc",
        "cwd": Path("/p/repo"),
        "name": "repo-1",
        "busy": False,
        "last_active": 1000.0,
        "entrypoint": "cli",
    }
    return Session(pid=pid, **defaults | fields)


def test_every_process_of_an_app_bundle_is_one_item_wherever_it_sits(proc):
    found = items(
        [
            proc(10, exe=BRAVE, memory=100),
            proc(11, ppid=10, exe=BRAVE_HELPER, memory=50),
            proc(12, ppid=1, exe=BRAVE_HELPER, memory=5),  # a crash handler launchd started
        ],
        {},
        1.0,
    )
    assert [(i.app, i.memory, sorted(i.pids)) for i in found] == [
        ("Brave Browser", 155, [10, 11, 12])
    ]


def test_a_process_running_its_parents_executable_joins_its_parent(proc):
    found = items(
        [proc(10, exe="/opt/brave/brave", memory=100), proc(11, ppid=10, exe="/opt/brave/brave")],
        {},
        1.0,
    )
    assert [sorted(i.pids) for i in found] == [[10, 11]]


def test_a_program_started_from_another_is_its_own_item(proc):
    found = items(
        [proc(10, exe="/bin/zsh"), proc(11, ppid=10, exe="/usr/local/bin/node", cwd=Path("/p"))],
        {},
        1.0,
    )
    assert sorted((i.app, i.pids[0], i.cwd) for i in found) == [
        ("node", 11, Path("/p")),
        ("zsh", 10, None),
    ]


def test_a_claude_session_claims_everything_started_under_it(proc):
    found = items(
        [
            proc(10, exe=CLAUDE, memory=100),
            proc(11, ppid=10, exe="/bin/bash", memory=5),
            proc(12, ppid=11, exe="/usr/local/bin/node", memory=20),
        ],
        {10: session(10)},
        1.0,
    )
    assert len(found) == 1
    assert (found[0].app, found[0].name, found[0].memory) == (CLAUDE_APP, "repo-1", 125)


def test_a_claude_sessions_place_and_idle_time_come_from_its_record(proc):
    [item] = items([proc(10, exe=CLAUDE, cwd=Path("/elsewhere"))], {10: session(10)}, 1.0)
    assert (item.cwd, item.idle_since, item.stop) == (Path("/p/repo"), 1000.0, "kill 10")
    assert item.note == "resume: cd /p/repo && claude --resume abc"


def test_a_busy_claude_session_has_no_idle_time(proc):
    [item] = items([proc(10, exe=CLAUDE)], {10: session(10, busy=True)}, 1.0)
    assert item.idle_since is None


def test_a_claude_process_without_a_record_is_still_a_session(proc):
    [item] = items([proc(10, exe=CLAUDE, cwd=Path("/p"))], {}, 1.0)
    assert (item.kind, item.cwd, item.idle_since) == ("claude", Path("/p"), None)


def test_the_container_vm_and_the_processes_serving_it_are_one_item(proc):
    found = items(
        [
            proc(10, name="com.apple.Virtualization.VirtualMachine", memory=1000),
            proc(11, exe="/opt/homebrew/bin/limactl", memory=50, cwd=Path("/p/repo")),
            proc(12, name="ssh", cmdline=["ssh: /Users/me/.colima/_lima/ssh.sock [mux]"]),
        ],
        {},
        1.0,
        vm_stop="colima stop",
    )
    assert [(i.app, i.name, i.memory, i.stop, i.cwd) for i in found] == [
        (VM_APP, "Colima", 1050, "colima stop", None)
    ]


def test_a_process_in_a_container_is_left_to_docker_to_count(proc):
    assert items([proc(10, exe="/usr/bin/postgres", container="f" * 64)], {}, 1.0) == []


def test_cpu_is_the_share_of_one_core_used_during_the_sample(proc):
    [item] = items([proc(10, exe="/bin/node", cpu=1.0)], {}, 2.0)
    assert item.cpu == 0.5
