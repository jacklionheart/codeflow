"""
Test suite for Prompt class with focus on path resolution and validation.
"""

import pytest
from pathlib import Path
from typing import List
from unittest.mock import patch
from loopflow.compose.prompt import Prompt, PromptError
from loopflow.io.file import resolve_codebase_path

@pytest.fixture(autouse=True)
def set_code_context_root(monkeypatch):
    monkeypatch.setenv("CODE_CONTEXT_ROOT", "/mock/root")

@pytest.fixture
def mock_resolve():
    """Provide mocked path resolution with consistent behavior."""
    with patch('loopflow.io.file.resolve_codebase_path') as mock:
        mock.return_value = Path('/mock/root/path').resolve()
        yield mock

@pytest.fixture
def sample_prompt_content():
    """Sample prompt content for testing."""
    return """
# Test Project

## Goal
Test implementation

## Output
src/test.py
tests/test_impl.py

## Context
src/lib/

## Team
- reviewer1
- reviewer2
"""

@pytest.fixture
def mock_resolve_ok():
    """Provide mocked path resolution with consistent behavior."""
    with patch('loopflow.io.file.resolve_codebase_path') as mock:
        mock.side_effect = lambda p, **kwargs: (
            p if isinstance(p, Path) and p.is_absolute()
            else Path('/mock/root') / str(p)
        ).resolve()
        yield mock

def test_prompt_path_resolution(mock_resolve_ok):
    """Test path resolution for different input types."""
    prompt = Prompt(
        path=Path("/mock/root/loopflow.md"),
        goal="Test goal",
        output_files=["test.py", Path("other/test.py")],
        team=["reviewer"]
    )
    
    assert str(prompt.output_files[0]) == "/mock/root/test.py"
    assert str(prompt.output_files[1]) == "/mock/root/other/test.py"

@pytest.mark.parametrize("invalid_input", [
    "",  # Empty path
    ".",  # Current directory
    "../",  # Parent directory
    "//",  # Double slash
])
def test_prompt_invalid_paths(invalid_input):
    """Test handling of invalid paths."""
    with patch('loopflow.io.file.resolve_codebase_path') as mock:
        mock.side_effect = ValueError("Invalid path")
        with pytest.raises(PromptError, match="Invalid.*path"):
            Prompt(
                path=Path("/mock/root/loopflow.md"),
                goal="Test goal",
                output_files=[invalid_input],
                team=["reviewer"]
            )

def test_prompt_team_parsing():
    """Test team member parsing from different formats."""
    prompt = Prompt(
        path=Path("/mock/root/loopflow.md"),
        goal="Test goal",
        output_files=["test.py"],
        team=[
            "- reviewer1",
            "reviewer2",
            "* reviewer3"
        ]
    )
    assert set(prompt.team) == {"reviewer1", "reviewer2", "reviewer3"}

def test_prompt_team_parsing(tmp_path):
    """Test team member parsing from different formats."""
    content = """
## Goal
Test goal
## Output
test.py
## Team
- reviewer1
reviewer2
* reviewer3
"""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text(content)
    
    with patch('loopflow.io.file.resolve_codebase_path'):
        prompt = Prompt.from_file(prompt_file)
        assert set(prompt.team) == {"reviewer1", "reviewer2", "reviewer3"}