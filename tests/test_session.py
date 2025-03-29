"""Test suite for session management."""

import asyncio
from pathlib import Path
import tempfile
import pytest

from loopflow.compose.session import Session, SessionError
from loopflow.compose.workflow import Job, WorkflowState
from .mock import MockUser

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def basic_session(mock_user, mock_provider):
    """Create a basic session with properly configured LLMs."""
    # Create mock LLMs
    llms = {
        "reviewer1": mock_provider.createLLM(
            name="reviewer1",
            system_prompt="Test system prompt",
        ),
        "reviewer2": mock_provider.createLLM(
            name="reviewer2", 
            system_prompt="Test system prompt",
        )
    }
    
    # Create session with required components
    session = Session(
        user=mock_user,
        providers={"mock": mock_provider},
        available_llms=llms,
        timeout=1.0
    )
    
    # Create temp directory for file operations
    session._temp_dir = Path(tempfile.mkdtemp())
    
    return session


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_timeout(basic_session, basic_prompt):
    """Test timeout handling with real async delay."""
    class SlowJob(Job):
        async def execute(self, context: WorkflowState) -> WorkflowState:
            await asyncio.sleep(0.2)  # Longer than timeout
            return context
    
    # Set a shorter timeout before running
    basic_session.timeout = 0.1
    
    # Create a pipeline that just has our slow job
    basic_session.pipeline = SlowJob()
    
    with pytest.raises(SessionError) as exc:
        await basic_session.run(basic_prompt)
        
    assert "TimeoutError" in str(exc.value)
    assert exc.value.context["status"] == "error"

@pytest.mark.asyncio
async def test_session_with_user_interaction(basic_session, basic_prompt):
    """Test session with specific user responses."""
    responses = [
        "Answer to question 1",
        "Answer to question 2",
        "Final answer"
    ]
    basic_session.user = MockUser(responses=responses)
    
    result = await basic_session.run(basic_prompt)
    assert result is not None
    assert "execution_time" in result
    assert result["status"] == "success"
    
@pytest.mark.asyncio
async def test_session_error_handling(basic_session, basic_prompt):
    """Test error handling with actual exceptions."""
    error_msg = "Test error"
    
    # Create an error-raising job
    class ErrorJob(Job):
        async def execute(self, context: WorkflowState) -> WorkflowState:
            raise Exception(error_msg)
    
    # Override the pipeline to use our error job
    basic_session.pipeline = ErrorJob()
    
    with pytest.raises(SessionError) as exc:
        await basic_session.run(basic_prompt)
    
    assert error_msg in str(exc.value)
    assert exc.value.context["status"] == "error"
