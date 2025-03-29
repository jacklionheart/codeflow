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
    # Mimic OpenAI ChatCompletion API response structure.
    return {
        "choices": [
            {
                "message": {
                    "content": "Test OpenAI response"
                }
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20
        }
    }

@pytest.mark.asyncio
async def test_openai_chat_success(config, mock_response):
    with patch("openai.resources.chat.Completions.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.return_value = mock_response

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")

        response = await llm.chat("Hello, OpenAI!")

        assert response == "Test OpenAI response"
        mock_acreate.assert_called_once()

        call_kwargs = mock_acreate.call_args[1]
        messages = call_kwargs["messages"]
        # Verify the last message is the current user prompt.
        assert messages[-1]["content"] == "Hello, OpenAI!"
        # Verify that the configured model is used.
        assert call_kwargs["model"] == "o3-mini-high"

@pytest.mark.asyncio
async def test_openai_conversation_history(config, mock_response):
    with patch("openai.resources.chat.Completions.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.return_value = mock_response

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")

        # Send two messages and check that history is maintained.
        await llm.chat("Hello, OpenAI!")
        await llm.chat("How are you?")

        call_kwargs = mock_acreate.call_args[1]
        messages = call_kwargs["messages"]
        # There should be at least two user messages in the conversation history.
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

    with patch("openai.resources.chat.Completions.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.side_effect = [response1, response2]

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")

        await llm.chat("Message 1")
        await llm.chat("Message 2")

        # Verify that usage tokens accumulate correctly.
        assert provider.usage.input_tokens == 25  # 10 + 15
        assert provider.usage.output_tokens == 45  # 20 + 25

@pytest.mark.asyncio
async def test_openai_error_handling(config):
    with patch("openai.resources.chat.Completions.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.side_effect = Exception("API Error")

        provider = OpenAI(config)
        llm = provider.createLLM("test", "You are a test assistant.")

        with pytest.raises(LLMError) as exc:
            await llm.chat("Hello")

        assert "API Error" in str(exc.value)
        assert mock_acreate.call_count >= 1

@pytest.mark.asyncio
async def test_openai_timeout(config):
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.2)  # simulate delay beyond the timeout
        raise asyncio.TimeoutError("Operation timed out")

    with patch("openai.resources.chat.Completions.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.side_effect = slow_response

        test_config = {
            "api_key": "test_openai_key",
            "timeout": 0.1,
            "max_retries": 1,
            "model": "o3-mini-high"
        }
        provider = OpenAI(test_config)
        llm = provider.createLLM("test", "You are a test assistant.")

        with pytest.raises(LLMError) as exc:
            await llm.chat("Hello")

        assert "timeout" in str(exc.value).lower()
