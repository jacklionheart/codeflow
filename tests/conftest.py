"""Shared test configuration and fixtures."""

import pytest
from pathlib import Path
from textwrap import dedent

from loopflow.compose.prompt import Prompt
from .mock import MockUser, MockProvider

@pytest.fixture
def basic_prompt(tmp_path: Path):
    """Create a basic prompt for testing."""
    return Prompt(
        path=tmp_path / "loopflow.md",
        goal="Build a simple test function",
        output_files=[tmp_path / "test_func.py"],
        team=["reviewer1", "reviewer2"],
        context_files=None
    )

@pytest.fixture
def valid_prompt_content():
    """Sample content for a valid prompt file."""
    return dedent("""
        # Test Project

        ## Goal
        Build a test component

        ## Output
        test_output.py
        utils.py

        ## Context
        src/lib

        ## Team
        - reviewer1
        - reviewer2
    """).lstrip()

@pytest.fixture
def tmp_prompt_file(tmp_path: Path, valid_prompt_content):
    """Create a temporary prompt file with valid content."""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(valid_prompt_content)
    return prompt_file

@pytest.fixture
def mock_user():
    """Mock user that provides predefined answers."""
    return MockUser()

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "accounts": {
            "anthropic": {
                "api_key": "test_key",
                "model": "test_model"
            }
        }
    }

@pytest.fixture
def mock_provider():
    """Get a mock provider from mock_llm."""
    provider = MockProvider()
    return provider
