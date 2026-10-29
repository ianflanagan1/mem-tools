import subprocess
from pathlib import Path

import pytest

from mem.projects import Locator, Place


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo at <root>/group/app, on branch main, with one commit."""
    path = tmp_path / "root" / "group" / "app"
    (path / "src").mkdir(parents=True)
    git("init", "--quiet", "--initial-branch", "main", cwd=path)
    git(
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "--quiet",
        "--allow-empty",
        "--message",
        "x",
        cwd=path,
    )
    return path


def test_a_directory_in_a_repo_is_placed_under_the_repo_and_its_branch(repo: Path):
    locator = Locator(repo.parents[1])
    assert locator.place(repo / "src") == Place("group/app", "main")


def test_worktrees_of_one_repo_are_placed_under_that_repo(repo: Path):
    worktree = repo.parents[1] / "app-feature"
    git("worktree", "add", "--quiet", "-b", "feature", str(worktree), cwd=repo)
    locator = Locator(repo.parents[1])
    assert locator.place(worktree) == Place("group/app", "feature (app-feature)")


def test_a_detached_worktree_is_named_as_detached(repo: Path):
    worktree = repo.parents[1] / "app-old"
    git("worktree", "add", "--quiet", "--detach", str(worktree), cwd=repo)
    assert Locator(repo.parents[1]).place(worktree) == Place("group/app", "detached (app-old)")


def test_a_folder_under_the_root_in_no_repo_is_its_own_project(tmp_path: Path):
    (tmp_path / "notes" / "deep").mkdir(parents=True)
    assert Locator(tmp_path).place(tmp_path / "notes" / "deep") == Place("notes")


def test_a_directory_outside_the_root_in_no_repo_has_no_place(tmp_path: Path):
    (tmp_path / "root").mkdir()
    (tmp_path / "elsewhere").mkdir()
    assert Locator(tmp_path / "root").place(tmp_path / "elsewhere") is None


def test_the_root_itself_has_no_place(tmp_path: Path):
    assert Locator(tmp_path).place(tmp_path) is None


def test_a_repo_outside_the_root_is_never_looked_at(repo: Path, tmp_path: Path):
    # Reading another app's folder, such as ~/Library/Containers/<app>, makes macOS ask the user.
    (tmp_path / "other-root").mkdir()
    assert Locator(tmp_path / "other-root").place(repo / "src") is None


def test_the_search_for_a_repo_stops_at_the_root(tmp_path: Path):
    git("init", "--quiet", cwd=tmp_path)
    (tmp_path / "root" / "notes").mkdir(parents=True)
    assert Locator(tmp_path / "root").place(tmp_path / "root" / "notes") == Place("notes")
