import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from typing import Dict, Any

from loopflow.llm.mate import MateConfig, MateError, Team
from loopflow.llm import LLM
from tests.mock import MockProvider

@pytest.fixture
def mock_llm_factory():
    """Create mock LLMs with independent response queues."""
    def create_mock():
        return AsyncMock(spec=LLM)
    return create_mock

@pytest.fixture
def mock_llms(mock_llm_factory):
    """Create a dictionary of mock LLMs."""
    return {
        "reviewer1": mock_llm_factory(),
        "reviewer2": mock_llm_factory()
    }

@pytest.fixture
def team(mock_llms):
    """Create a Team instance with mock LLMs."""
    return Team({"mock": MockProvider()}, mock_llms)

@pytest.fixture
def mate_file_content():
    """Sample content for a mate markdown file."""
    return """## Description
A test reviewer role.

## System Prompt
You are a test reviewer.

## Provider
mock
"""

@pytest.mark.asyncio
async def test_team_query_parallel_success(team, mock_llms):
    """Test successful parallel query execution."""
    # Setup distinct responses for each mate
    mock_llms["reviewer1"].chat.return_value = "Response 1"
    mock_llms["reviewer2"].chat.return_value = "Response 2"
    
    prompt = "Test prompt {name}"
    args = {"key": "value"}
    
    responses = await team.query_parallel(prompt, args)
    
    assert len(responses) == 2
    assert responses["reviewer1"] == "Response 1"
    assert responses["reviewer2"] == "Response 2"
    
    # Verify prompt formatting for each mate
    mock_llms["reviewer1"].chat.assert_called_once_with(
        prompt.format(name="reviewer1", **args)
    )
    mock_llms["reviewer2"].chat.assert_called_once_with(
        prompt.format(name="reviewer2", **args)
    )

@pytest.mark.asyncio
async def test_team_query_parallel_partial_failure(team, mock_llms):
    """Test handling of failures from some team members."""
    error = Exception("API Error")
    mock_llms["reviewer1"].chat.side_effect = error
    mock_llms["reviewer2"].chat.return_value = "Response 2"
    
    responses = await team.query_parallel("Test prompt {name}", {})
    
    assert len(responses) == 2
    assert responses["reviewer1"] == f"Error: {str(error)}"
    assert responses["reviewer2"] == "Response 2"

def test_mate_from_file_success(tmp_path, mate_file_content):
    """Test successful MateConfig creation from file."""
    mate_file = tmp_path / "test_mate.md"
    mate_file.write_text(mate_file_content)
    
    mate = MateConfig.from_file(mate_file)
    
    assert mate.name == "test_mate"
    assert mate.provider == "mock"
    assert mate.system_prompt == "You are a test reviewer."

def test_mate_from_file_missing_section(tmp_path):
    """Test error handling for missing required sections."""
    incomplete_content = """## Description
A test reviewer role.

## Provider
mock
"""
    mate_file = tmp_path / "incomplete_mate.md"
    mate_file.write_text(incomplete_content)
    
    with pytest.raises(MateError, match="Member file missing System Prompt section"):
        MateConfig.from_file(mate_file)

def test_mate_section_parsing():
    """Test the section parsing logic."""
    content = """## Section1
Content 1

## Section2
Content 2
More content
"""
    sections = MateConfig._parse_sections(content)
    
    assert len(sections) == 2
    assert sections["Section1"] == "Content 1"
    assert sections["Section2"] == "Content 2\nMore content"

@pytest.mark.asyncio
async def test_team_empty_mates():
    """Test team behavior with no mates."""
    team = Team(MockProvider(), {})
    result = await team.query_parallel("Test", {})
    assert result == {}, "Empty team should return empty results"