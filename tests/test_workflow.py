"""Tests for the workflow implementation."""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock

from loopflow.compose.workflow import (
    Sequential,
    Clarify, Draft, Review, Synthesize,
    default_pipeline, WorkflowError
)
from loopflow.compose.prompt import Prompt
from loopflow.llm.team import Team
from loopflow.compose.workflow import WorkflowState
from .mock import MockProvider

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_mate():
    """Creates a mock LLM instance."""
    return AsyncMock(
        chat=AsyncMock(return_value="Mock response")
    )

@pytest.fixture
def mock_team(mock_mate):
    """Creates a team with mock LLMs."""
    llms = {"reviewer1": mock_mate, "reviewer2": mock_mate}
    team = Team({"mock": MockProvider()}, llms)
    # Mock the query_parallel method to have more control over responses
    team.query_parallel = AsyncMock(return_value={
        "reviewer1": "Mock response",
        "reviewer2": "Mock response"
    })
    return team

@pytest.fixture
def mock_user():
    """Creates a mock user that returns predefined responses."""
    return AsyncMock(
        chat=AsyncMock(return_value="Mock user response")
    )

@pytest.fixture
def basic_prompt(tmp_path):
    """Creates a basic test prompt with absolute paths."""
    # Workflows assume absolute paths
    test_file = (tmp_path / "test.py").resolve()
    return Prompt(
        goal="Test goal",
        output_files=[test_file],
        team=["reviewer1", "reviewer2"],
        context_files=None
    )


@pytest.fixture
def basic_state(basic_prompt, mock_team, mock_user):
    """Creates a basic context for testing."""
    state = WorkflowState(
        prompt=basic_prompt,
        team=mock_team
    )
    state.user = mock_user
    return state

# -----------------------------------------------------------------------------
# Individual Job Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clarify_job(basic_state):
    """Test clarification job execution."""
    job = Clarify()
    result = await job.execute(basic_state)
    
    # Verify team was queried
    assert basic_state.team.query_parallel.called
    
    # Verify clarification was stored
    assert result.clarifications is not None
    assert "Mock response" in str(result.clarifications)

@pytest.mark.asyncio
async def test_draft_job(basic_state):
    """Test draft generation job."""
    job = Draft()
    result = await job.execute(basic_state)
    
    # Verify drafts were created for each team member
    assert len(result.drafts) == len(basic_state.team.llms)
    
    # Get absolute path from prompt
    test_file = basic_state.prompt.output_files[0]
    
    # Verify draft content
    author_drafts = result.drafts["reviewer1"]
    assert test_file in author_drafts
    assert "Mock response" in author_drafts[test_file]

@pytest.mark.asyncio
async def test_review_job(basic_state):
    """Test review job execution."""
    # Setup some drafts
    basic_state.drafts = {
        "reviewer1": {Path("test.py"): "test code"},
        "reviewer2": {Path("test.py"): "test code"}
    }
    
    job = Review()
    result = await job.execute(basic_state)
    
    # Verify reviews were created
    assert len(result.reviews) == 2  # Two team
    for reviewer in ["reviewer1", "reviewer2"]:
        assert reviewer in result.reviews
        assert "reviewer1" in result.reviews[reviewer]
        assert "Mock response" in result.reviews[reviewer]["reviewer1"]

@pytest.mark.asyncio
async def test_synthesize_job(basic_state):
    """Test synthesis job execution."""
    # Get absolute path from prompt
    test_file = basic_state.prompt.output_files[0]
    
    # Setup drafts and reviews with absolute paths
    basic_state.drafts = {
        "reviewer1": {test_file: "test code"},
        "reviewer2": {test_file: "test code"}
    }
    basic_state.reviews = {
        "reviewer1": {"reviewer1": "review 1", "reviewer2": "review 2"},
        "reviewer2": {"reviewer1": "review 1", "reviewer2": "review 2"}
    }

    job = Synthesize()
    result = await job.execute(basic_state)

    assert test_file in result.outputs
    assert result.outputs[test_file] == "Mock response"

# -----------------------------------------------------------------------------
# Pipeline Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sequential_job_execution(basic_state):
    """Test sequential execution of multiple jobs."""
    jobs = [
        Clarify(),
        Draft(),
        Review(),
        Synthesize()
    ]
    
    pipeline = Sequential(jobs)
    result = await pipeline.execute(basic_state)
    
    # Verify full pipeline execution
    assert result.clarifications is not None
    assert len(result.drafts) > 0
    assert len(result.reviews) > 0
    assert len(result.outputs) > 0

@pytest.mark.asyncio
async def test_default_pipeline(basic_state):
    """Test the default pipeline creation and execution."""
    pipeline = default_pipeline()
    result = await pipeline.execute(basic_state)
    
    # Verify pipeline produced expected outputs
    assert result.clarifications is not None
    assert len(result.drafts) > 0
    assert len(result.reviews) > 0
    
    test_file = basic_state.prompt.output_files[0]  # Use absolute path from prompt
    assert test_file in result.outputs

# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_error_handling(basic_state):
    """Test error handling in job execution."""
    # Make the team's query_parallel raise an exception
    basic_state.team.query_parallel.side_effect = Exception("Test error")
    
    job = Clarify()
    with pytest.raises(WorkflowError) as exc:
        await job.execute(basic_state)
    
    assert "Clarification failed" in str(exc.value)
    assert exc.value.context["stage"] == "clarify"

@pytest.mark.asyncio
async def test_sequential_error_handling(basic_state):
    """Test error handling in sequential job execution."""
    basic_state.team.query_parallel = AsyncMock(side_effect=Exception("Test error"))
    
    pipeline = Sequential([Clarify()])
    with pytest.raises(WorkflowError) as exc:
        await pipeline.execute(basic_state)
    
    assert "Clarification failed" in str(exc.value)
    assert exc.value.context["stage"] == "clarify"
    assert str(exc.value.context["error"]) == "Test error"
