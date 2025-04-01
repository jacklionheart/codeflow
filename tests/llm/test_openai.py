import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from loopflow.llm.openai import OpenAI, GPT
from loopflow.llm import LLMError

@pytest.fixture
def config():
    return {
        "api_key": "test_openai_key",
        "timeout": 1.0,
        "max_retries": 1,
        "model": "o3-mini-high"
    }

@pytest.fixture
def mock_response():
    # Mimic the structure of a successful OpenAI ChatCompletion response.
    return {
        "choices": [
            {
                "message": {"content": "Test OpenAI response"}
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20
        }
    }

@pytest.mark.asyncio
async def test_openai_chat_success(config, mock_response):
    # Patch the AsyncOpenAI constructor so that our provider uses a mock client.
    with patch("openai.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        # When chat.completions.create is called, return our mock response.
        mock_client.chat.completions.create.return_value = mock_response
        mock_async_openai.return_value = mock_client

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        response = await llm.chat("Hello, OpenAI!")
        
        assert response == "Test OpenAI response"
        mock_client.chat.completions.create.assert_called_once()
        
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        # Verify that the last message is the current user prompt.
        assert messages[-1]["content"] == "Hello, OpenAI!"
        # Verify that the configured model is used.
        assert call_kwargs["model"] == "o3-mini-high"

@pytest.mark.asyncio
async def test_openai_conversation_history(config, mock_response):
    with patch("openai.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_async_openai.return_value = mock_client

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        # Send two messages sequentially.
        await llm.chat("Hello, OpenAI!")
        await llm.chat("How are you?")
        
        # Check that conversation history is passed into the API call.
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assert len(user_messages) >= 2

@pytest.mark.asyncio
async def test_openai_token_tracking(config):
    # Prepare two responses with different token usage.
    response1 = {
        "choices": [
            {"message": {"content": "Response 1"}}
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20
        }
    }
    response2 = {
        "choices": [
            {"message": {"content": "Response 2"}}
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 25
        }
    }
    with patch("openai.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        # Simulate sequential responses.
        mock_client.chat.completions.create.side_effect = [response1, response2]
        mock_async_openai.return_value = mock_client

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        await llm.chat("Message 1")
        await llm.chat("Message 2")

        usage = provider.usage
        # Verify that token usage is accumulated correctly.
        assert usage.input_tokens == 25  # 10 + 15
        assert usage.output_tokens == 45  # 20 + 25

@pytest.mark.asyncio
async def test_openai_error_handling(config):
    with patch("openai.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        # Simulate an API error.
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_async_openai.return_value = mock_client

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        with pytest.raises(LLMError) as excinfo:
            await llm.chat("Hello")
        # The error message should mention the API error.
        assert "api error" in str(excinfo.value).lower()
        assert mock_client.chat.completions.create.call_count >= 1

@pytest.mark.asyncio
async def test_openai_timeout(config):
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.2)  # Delay longer than the timeout setting.
        raise asyncio.TimeoutError("Operation timed out")
    
    with patch("openai.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = slow_response
        mock_async_openai.return_value = mock_client

        test_config = {
            "api_key": "test_openai_key",
            "timeout": 0.1,  # Set a short timeout.
            "max_retries": 1,
            "model": "o3-mini-high"
        }
        provider = OpenAI(test_config)
        llm = provider.createLLM("test", "You are a test assistant.")
        with pytest.raises(LLMError) as excinfo:
            await llm.chat("Hello")
        # Check that the error message indicates a timeout.
        assert "timeout" in str(excinfo.value).lower()
