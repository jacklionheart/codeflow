import pytest
from pathlib import Path
from codeflow.io.git import auto_checkpoint
import codeflow.io.git as git_mod


def test_auto_checkpoint_commits_on_dev_branch(monkeypatch, tmp_path: Path, basic_prompt):
    """
    When auto-checkpointing is enabled (e.g. on a dev branch), auto_checkpoint should
    stage files and create a checkpoint commit.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Simulate enabled checkpointing (e.g. non-main branch and a valid git repo)
    monkeypatch.setattr(git_mod, "should_auto_checkpoint", lambda path: True)

    stage_called = False
    commit_called = False

    def fake_stage_all_files(path: Path) -> bool:
        nonlocal stage_called
        stage_called = True
        return True

    def fake_create_checkpoint(path: Path, command: str, details: dict) -> bool:
        nonlocal commit_called
        commit_called = True
        return True

    monkeypatch.setattr(git_mod, "stage_all_files", fake_stage_all_files)
    monkeypatch.setattr(git_mod, "create_checkpoint", fake_create_checkpoint)

    result = auto_checkpoint(project_dir, "test_command", basic_prompt)

    assert result is True, "auto_checkpoint should return True on successful commit"
    assert stage_called, "stage_all_files should be called when checkpointing is enabled"
    assert commit_called, "create_checkpoint should be called when checkpointing is enabled"


def test_auto_checkpoint_disabled(monkeypatch, tmp_path: Path):
    """
    When checkpointing is explicitly disabled (via config or other means), auto_checkpoint
    should not stage or commit any changes.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Simulate disabled checkpointing
    monkeypatch.setattr(git_mod, "should_auto_checkpoint", lambda path: False)

    # These functions should not be called; if they are, we raise an error.
    def fake_stage_all_files(path: Path) -> bool:
        raise Exception("stage_all_files should not be called when checkpointing is disabled")

    def fake_create_checkpoint(path: Path, command: str, details: dict) -> bool:
        raise Exception("create_checkpoint should not be called when checkpointing is disabled")

    monkeypatch.setattr(git_mod, "stage_all_files", fake_stage_all_files)
    monkeypatch.setattr(git_mod, "create_checkpoint", fake_create_checkpoint)

    result = auto_checkpoint(project_dir, "test_command", {"info": "details"})
    assert result is True, "auto_checkpoint should return True when checkpointing is disabled"


def test_auto_checkpoint_no_commit_on_main_branch(monkeypatch, tmp_path: Path):
    """
    When the current branch is 'main', auto_checkpoint should not perform any staging
    or commit, even if the repository is valid.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Simulate that the current branch is "main" by having should_auto_checkpoint return False.
    def fake_should_auto_checkpoint(path: Path) -> bool:
        # Simulate a valid git repo on the 'main' branch.
        return False

    monkeypatch.setattr(git_mod, "should_auto_checkpoint", fake_should_auto_checkpoint)

    # These functions should not be called on main branch.
    def fake_stage_all_files(path: Path) -> bool:
        raise Exception("stage_all_files should not be called on the main branch")

    def fake_create_checkpoint(path: Path, command: str, details: dict) -> bool:
        raise Exception("create_checkpoint should not be called on the main branch")

    monkeypatch.setattr(git_mod, "stage_all_files", fake_stage_all_files)
    monkeypatch.setattr(git_mod, "create_checkpoint", fake_create_checkpoint)

    result = auto_checkpoint(project_dir, "test_command", {"info": "details"})
    assert result is True, "auto_checkpoint should return True without committing on the main branch"
