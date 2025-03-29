"""
Test suite for Prompt class with focus on path resolution and validation.
"""

import pytest
from pathlib import Path
from typing import List
from unittest.mock import patch
from loopflow.compose.prompt import Prompt, PromptError
from loopflow.compose.file import resolve_codebase_path

@pytest.fixture
def mock_resolve():
    """Provide mocked path resolution with consistent behavior."""
    with patch('loopflow.run.file.resolve_codebase_path') as mock:
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
    with patch('loopflow.run.file.resolve_codebase_path') as mock:
        mock.side_effect = lambda p, **kwargs: (
            p if isinstance(p, Path) and p.is_absolute()
            else Path('/mock/root') / str(p)
        ).resolve()
        yield mock

def test_prompt_path_resolution(mock_resolve_ok):
    """Test path resolution for different input types."""
    prompt = Prompt(
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
    with patch('loopflow.run.prompt.resolve_codebase_path') as mock:
        mock.side_effect = ValueError("Invalid path")
        with pytest.raises(PromptError, match="Invalid.*path"):
            Prompt(
                goal="Test goal",
                output_files=[invalid_input],
                team=["reviewer"]
            )

def test_prompt_team_parsing():
    """Test team member parsing from different formats."""
    prompt = Prompt(
        goal="Test goal",
        output_files=["test.py"],
        team=[
            "- reviewer1",
            "reviewer2",
            "* reviewer3"
        ]
    )
    assert set(prompt.team) == {"reviewer1", "reviewer2", "reviewer3"}

@pytest.mark.parametrize("platform,path,expected", [
    ('posix', 'path/to/file.py', '/mock/root/path/to/file.py'),
    ('nt', 'path\\to\\file.py', '/mock/root/path/to/file.py'),
])

def test_prompt_cross_platform_paths(mock_resolve, platform, path, expected):
    """Test path handling across platforms."""
    with patch('os.name', platform):
        # Create mock path appropriate for platform
        if platform == 'nt':
            expected_path = Path('\\mock\\root\\path\\to\\file.py')
        else:
            expected_path = Path('/mock/root/path/to/file.py')

        mock_resolve.side_effect = lambda p, **kwargs: expected_path

        prompt = Prompt(
            goal="Test goal",
            output_files=[path],
            team=["reviewer"]
        )

        # Check against platform-specific path
        assert prompt.output_files[0] == expected_path


def test_prompt_read_write_modes(mock_resolve):
    """Test path resolution modes for reading and writing."""
    prompt = Prompt(
        goal="Test goal",
        output_files=["output.py"],
        team=["reviewer"],
        context_files=["src/"]
    )
    
    calls = mock_resolve.call_args_list
    assert calls[0].kwargs.get('for_reading') is False  # output file
    assert calls[1].kwargs.get('for_reading') is True   # context file

@pytest.mark.parametrize("test_input", [
    {"goal": "", "output_files": ["test.py"], "team": ["reviewer"]},
    {"goal": "Test", "output_files": [], "team": ["reviewer"]},
    {"goal": "Test", "output_files": ["test.py"], "team": []},
])
def test_prompt_validation(mock_resolve, test_input):
    """Test prompt validation requirements."""
    with pytest.raises(PromptError):
        Prompt(**test_input)

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
    
    with patch('loopflow.run.prompt.resolve_codebase_path'):
        prompt = Prompt.from_file(prompt_file)
        assert set(prompt.team) == {"reviewer1", "reviewer2", "reviewer3"}