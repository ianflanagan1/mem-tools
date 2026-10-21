"""Placing a working directory under its project: the repo, and the worktree within it.

Worktrees of one repo share its git directory, so they're grouped by that rather than by where
their folders are. A folder under the projects root that isn't in a repo is its own project,
named by its folder directly under the root.

Git's files are read directly rather than through git, which would take a process for each of
the hundreds of directories processes run in. Only folders under the root are read: many
processes run in other apps' folders, such as ~/Library/Containers/<app>, and reading those
makes macOS ask the user to allow it.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Place:
    project: str
    worktree: str | None = None


class Locator:
    """Places directories under projects, remembering each directory's place."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._places: dict[Path, Place | None] = {}

    def place(self, directory: Path) -> Place | None:
        """Where directory belongs, or None when it isn't under the root."""
        if directory not in self._places:
            self._places[directory] = self._locate(directory)
        return self._places[directory]

    def _locate(self, directory: Path) -> Place | None:
        if not directory.is_relative_to(self.root) or directory == self.root:
            return None
        if (repo := _repo(directory, self.root)) is not None:
            top, main, branch = repo
            worktree = branch if top == main else f"{branch} ({self._name(top)})"
            return Place(self._name(main), worktree)
        return Place(directory.relative_to(self.root).parts[0])

    def _name(self, path: Path) -> str:
        """path from the root, or from home when it's outside the root."""
        for base, prefix in ((self.root, ""), (Path.home(), "~/")):
            if path.is_relative_to(base) and path != base:
                return prefix + str(path.relative_to(base))
        return str(path)


def _repo(directory: Path, root: Path) -> tuple[Path, Path, str] | None:
    """The worktree directory is in, the repo's main worktree, and the branch checked out,
    looking no higher than the folders directly under root."""
    for top in (directory, *directory.parents):
        if top == root:
            return None
        dot_git = top / ".git"
        if dot_git.is_dir():
            return top, top, _branch(dot_git)
        if dot_git.is_file():
            gitdir = _gitdir(dot_git, top)
            if gitdir is None:
                return None
            common = gitdir / "commondir"
            if not common.is_file():  # a submodule, which is its own repo
                return top, top, _branch(gitdir)
            common_dir = (gitdir / common.read_text().strip()).resolve()
            main = common_dir.parent if common_dir.name == ".git" else common_dir.with_suffix("")
            return top, main, _branch(gitdir)
    return None


def _gitdir(dot_git: Path, top: Path) -> Path | None:
    text = dot_git.read_text().strip()
    if not text.startswith("gitdir:"):
        return None
    return (top / text.removeprefix("gitdir:").strip()).resolve()


def _branch(gitdir: Path) -> str:
    try:
        head = (gitdir / "HEAD").read_text().strip()
    except OSError:
        return "detached"
    return head.removeprefix("ref: refs/heads/") if head.startswith("ref: ") else "detached"
