"""Claude Code sessions: which process is which session, where it works and when it was last used.

Claude Code writes ~/.claude/sessions/<pid>.json for each running session, with its id, working
directory, name and status. That isn't a documented format, so each field is read only if it's
there, and the last activity is also taken from the session's transcript under
~/.claude/projects, which is written on every message.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from mem.model import Proc


@dataclass
class Session:
    pid: int
    session_id: str | None
    cwd: Path | None
    name: str | None
    busy: bool
    last_active: float | None
    entrypoint: str | None


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def sessions(config: Path) -> dict[int, Session]:
    """The sessions recorded under config, by pid. A record that can't be read is skipped."""
    found = {}
    for path in (config / "sessions").glob("*.json"):
        try:
            record = json.loads(path.read_text())
            pid = int(record["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        session_id = record.get("sessionId")
        updated = record.get("updatedAt")
        times = [updated / 1000] if isinstance(updated, int | float) else []
        if session_id and (transcript := _transcript(config, session_id)):
            times.append(transcript.stat().st_mtime)
        found[pid] = Session(
            pid=pid,
            session_id=session_id,
            cwd=Path(record["cwd"]) if record.get("cwd") else None,
            name=record.get("name"),
            busy=record.get("status") == "busy",
            last_active=max(times) if times else None,
            entrypoint=record.get("entrypoint"),
        )
    return found


def _transcript(config: Path, session_id: str) -> Path | None:
    return next((config / "projects").glob(f"*/{session_id}.jsonl"), None)


def is_claude(proc: Proc) -> bool:
    """Whether a process is Claude Code, whether its native binary or its npm package."""
    if Path(proc.exe).name == "claude" or proc.name == "claude":
        return True
    return any("@anthropic-ai/claude-code" in arg for arg in proc.cmdline[:2])
