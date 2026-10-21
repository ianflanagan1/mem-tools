# mem-tools

`mem` shows how close a development machine is to running out of memory, what's using it, and what's safe to stop. It's for the kind of machine that builds up idle Claude Code sessions and forgotten Docker Compose stacks across many projects and worktrees. It isn't meant for servers.

Runs on macOS and Linux. Built on [cli-kit](../cli-kit), so its help and status lines work like those of my other command line tools.

```
$ mem
Top apps
Visual Studio Code                  2.1 GB  20 processes
Container VM                        1.3 GB  4 processes
Claude Code                         1.3 GB  ×10 · 12 processes
Brave Browser                       917 MB  10 processes
Claude                              831 MB  9 processes

Top projects
claude/commit-skills                1.2 GB  claude ×9 (8 idle) · bash
dog-cafe                            232 MB  claude (1 idle) · bash · compose

5 suggestions, freeing up to 1.6 GB: run `mem suggest`.

➖ Memory pressure normal: 30 GB available of 48 GB, no swap in use.
```

## Commands

`mem help` lists them, and `mem help <command>` shows one in full. Every command watches CPU use for a second (`--sample`) to tell idle from busy, and counts something as idle after an hour unused (`--idle 30m`, `2h`, `1d`).

| Command | Shows |
|---|---|
| `mem` or `mem status` | The memory pressure, the five apps and five projects using the most, and how much the suggestions would free |
| `mem apps [<filter>]` | Memory use by app. Name an app to see inside it, such as each Claude session with how long it's been idle |
| `mem projects [<filter>]` | Memory use by repo and worktree under `~/projects` (or `$MEM_PROJECTS`): the Claude sessions working there, the compose projects started there, and any other process running there. Name a project to see each session and container |
| `mem suggest` | What's worth stopping, why, and the command that stops it. It never runs those commands itself |

`--depth <levels>` shows more or fewer levels of any listing.

## What it counts

- **Memory** is what stopping a process would free, as near as the OS says: the footprint on macOS (Activity Monitor's Memory column), and the proportional set size on Linux. Plain resident size counts shared memory once for every process that maps it.
- **Pressure** comes from the kernel: macOS's memory pressure level, and Linux's pressure stall information (`/proc/pressure/memory`). Free memory alone misleads, since caches fill what's free and are given up on demand.
- **Apps:** every process of a macOS app bundle counts as one app, and so does a process running its parent's executable, as a browser's helpers do on Linux. A Claude Code session includes the shells and MCP servers it started.
- **Projects:** a working directory belongs to its git repo, and worktrees of one repo are grouped under it. Compose projects are placed by the directory they were started from.
- **Containers on macOS** run in a VM (Colima or Docker Desktop). The host sees only the VM, so stopping containers frees memory inside it for other containers, not for macOS. Stopping the VM gives it back. On Linux, containers are host processes and are counted once, under Docker.

## What it suggests

- **likely:** a Claude Code session idle for longer than `--idle`. Its transcript is kept, so the `claude --resume` line it prints brings it back.
- **maybe:** a compose project whose containers used no CPU during the sample, in a worktree with no Claude session active within `--idle`. You may be working there without Claude.
- The container VM, when no containers are running (likely), or when every running one is suggested (maybe).

It never suggests the Claude session it was run from.

Claude Code's sessions are read from `~/.claude/sessions`, which isn't a documented format, so a Claude Code update may change what `mem` can tell about them.

## Setup

```sh
cd ~/projects/cli/mem-tools
devbox run setup   # uv sync, then links mem into ~/.local/bin
devbox run test    # pytest
devbox run lint    # ruff check and format
```
