import json
import os
from pathlib import Path

from mem.claude import is_claude, sessions


def record(config: Path, pid: int, **fields) -> None:
    (config / "sessions").mkdir(parents=True, exist_ok=True)
    data = {"pid": pid, "sessionId": "s-1", "cwd": "/p/app", "name": "app-1", "status": "idle"}
    (config / "sessions" / f"{pid}.json").write_text(json.dumps(data | fields))


def test_a_session_is_read_from_its_record(tmp_path: Path):
    record(tmp_path, 42, updatedAt=1_000_000)
    s = sessions(tmp_path)[42]
    assert (s.session_id, s.cwd, s.name, s.busy) == ("s-1", Path("/p/app"), "app-1", False)
    assert s.last_active == 1000.0


def test_a_session_was_last_active_when_its_transcript_was_last_written(tmp_path: Path):
    record(tmp_path, 42, updatedAt=1_000_000)
    transcript = tmp_path / "projects" / "-p-app" / "s-1.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("{}\n")
    os.utime(transcript, (5000, 5000))
    assert sessions(tmp_path)[42].last_active == 5000


def test_a_busy_session_is_marked_busy(tmp_path: Path):
    record(tmp_path, 42, status="busy")
    assert sessions(tmp_path)[42].busy


def test_a_record_missing_its_optional_fields_is_still_a_session(tmp_path: Path):
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "7.json").write_text('{"pid": 7}')
    s = sessions(tmp_path)[7]
    assert (s.session_id, s.cwd, s.last_active, s.busy) == (None, None, None, False)


def test_a_record_that_cant_be_read_is_skipped(tmp_path: Path):
    (tmp_path / "sessions").mkdir()
    (tmp_path / "sessions" / "1.json").write_text("not json")
    (tmp_path / "sessions" / "2.json").write_text('{"name": "no pid"}')
    assert sessions(tmp_path) == {}


def test_no_sessions_folder_means_no_sessions(tmp_path: Path):
    assert sessions(tmp_path) == {}


def test_claude_is_recognised_as_its_native_binary_or_its_npm_package(proc):
    assert is_claude(proc(1, exe="/x/native-binary/claude"))
    node = ["node", "/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js"]
    assert is_claude(proc(2, exe="/usr/bin/node", cmdline=node))
    assert not is_claude(proc(3, exe="/usr/bin/node", cmdline=["node", "server.js"]))
