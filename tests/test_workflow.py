"""Tests for the workflow implementation."""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from loopflow.workflow import (
    Context, Job, Sequential,
    Clarify, Draft, Review, Synthesize,
    default_pipeline, WorkflowError
)
from loopflow.prompt import Prompt
from loopflow.team import Team

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
    team = Team(llms)
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
def basic_prompt():
    """Creates a basic test prompt."""
    return Prompt(
        goal="Test goal",
        output_files=[Path("test.py")],
        reviewers=["reviewer1", "reviewer2"],
        context_files=None
    )

@pytest.fixture
def basic_context(basic_prompt, mock_team, mock_user):
    """Creates a basic context for testing."""
    context = Context(
        prompt=basic_prompt,
        team=mock_team
    )
    context.user = mock_user
    return context

# -----------------------------------------------------------------------------
# Individual Job Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clarify_job(basic_context):
    """Test clarification job execution."""
    job = Clarify()
    result = await job.execute(basic_context)
    
    # Verify team was queried
    assert basic_context.team.query_parallel.called
    
    # Verify clarification was stored
    assert result.clarifications is not None
    assert "Mock response" in str(result.clarifications)

@pytest.mark.asyncio
async def test_draft_job(basic_context):
    """Test draft generation job."""
    job = Draft()
    result = await job.execute(basic_context)
    
    # Verify drafts were created for each team member
    assert len(result.drafts) == len(basic_context.team.llms)
    
    # Verify draft content
    author_drafts = result.drafts["reviewer1"]
    assert Path("test.py") in author_drafts
    assert "Mock response" in author_drafts[Path("test.py")]

@pytest.mark.asyncio
async def test_review_job(basic_context):
    """Test review job execution."""
    # Setup some drafts
    basic_context.drafts = {
        "reviewer1": {Path("test.py"): "test code"},
        "reviewer2": {Path("test.py"): "test code"}
    }
    
    job = Review()
    result = await job.execute(basic_context)
    
    # Verify reviews were created
    assert len(result.reviews) == 2  # Two reviewers
    for reviewer in ["reviewer1", "reviewer2"]:
        assert reviewer in result.reviews
        assert "reviewer1" in result.reviews[reviewer]
        assert "Mock response" in result.reviews[reviewer]["reviewer1"]

@pytest.mark.asyncio
async def test_synthesize_job(basic_context):
    """Test synthesis job execution."""
    # Setup drafts and reviews
    basic_context.drafts = {
        "reviewer1": {Path("test.py"): "test code"},
        "reviewer2": {Path("test.py"): "test code"}
    }
    basic_context.reviews = {
        "reviewer1": {"reviewer1": "review 1", "reviewer2": "review 2"},
        "reviewer2": {"reviewer1": "review 1", "reviewer2": "review 2"}
    }
    
    job = Synthesize()
    result = await job.execute(basic_context)
    
    # Verify outputs were created
    assert Path("test.py") in result.outputs
    assert "Mock response" in result.outputs[Path("test.py")]

# -----------------------------------------------------------------------------
# Pipeline Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sequential_job_execution(basic_context):
    """Test sequential execution of multiple jobs."""
    jobs = [
        Clarify(),
        Draft(),
        Review(),
        Synthesize()
    ]
    
    pipeline = Sequential(jobs)
    result = await pipeline.execute(basic_context)
    
    # Verify full pipeline execution
    assert result.clarifications is not None
    assert len(result.drafts) > 0
    assert len(result.reviews) > 0
    assert len(result.outputs) > 0

@pytest.mark.asyncio
async def test_default_pipeline(basic_context):
    """Test the default pipeline creation and execution."""
    pipeline = default_pipeline()
    result = await pipeline.execute(basic_context)
    
    # Verify pipeline produced expected outputs
    assert result.clarifications is not None
    assert len(result.drafts) > 0
    assert len(result.reviews) > 0
    assert Path("test.py") in result.outputs

# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_error_handling(basic_context):
    """Test error handling in job execution."""
    # Make the team's query_parallel raise an exception
    basic_context.team.query_parallel.side_effect = Exception("Test error")
    
    job = Clarify()
    with pytest.raises(WorkflowError) as exc:
        await job.execute(basic_context)
    
    assert "Clarification failed" in str(exc.value)
    assert exc.value.context["stage"] == "clarify"

@pytest.mark.asyncio
async def test_sequential_error_handling(basic_context):
    """Test error handling in sequential job execution."""
    # Set up mock to fail on second call
    side_effect_called = False
    
    async def side_effect(*args, **kwargs):
        nonlocal side_effect_called
        if not side_effect_called:
            side_effect_called = True
            return {"reviewer1": "Mock response", "reviewer2": "Mock response"}
        raise Exception("Test error")
    
    basic_context.team.query_parallel.side_effect = side_effect
    
    pipeline = Sequential([Clarify(), Draft()])
    with pytest.raises(WorkflowError) as exc:
        await pipeline.execute(basic_context)
    
    assert "Draft generation failed" in str(exc.value)
    assert exc.value.context["stage"] == "draft"