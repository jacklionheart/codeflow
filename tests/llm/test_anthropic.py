import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from loopflow.llm import LLMError
from loopflow.llm.anthropic import Anthropic

@pytest.mark.asyncio
async def test_anthropic_chat(config, mock_response):
    """Test basic chat functionality with Anthropic."""
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        provider = Anthropic(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        response = await llm.chat("Hello")
        
        assert response == "Test response"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['model'] == "claude-3-5-sonnet-20241022"
        assert len(call_kwargs['messages']) > 0

@pytest.mark.asyncio
async def test_anthropic_conversation_history(config, mock_response):
    """Test that conversation history is maintained."""
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        provider = Anthropic(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        # First message
        await llm.chat("Hello")
        # Second message
        await llm.chat("How are you?", include_history=True)
        
        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs['messages']
        assert len(messages) >= 2  # Should include both interactions

@pytest.mark.asyncio
async def test_anthropic_token_tracking(config):
    """Test token usage tracking."""
    response1 = type('Response', (), {
        'content': [
            type('Content', (), {
                'text': 'Response 1'
            })()
        ],
        'usage': type('Usage', (), {
            'input_tokens': 10,
            'output_tokens': 20
        })
    })()
    
    response2 = type('Response', (), {
        'content': [
            type('Content', (), {
                'text': 'Response 2'
            })()
        ],
        'usage': type('Usage', (), {
            'input_tokens': 15,
            'output_tokens': 25
        })
    })()
    
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [response1, response2]
        mock_anthropic.return_value = mock_client
        
        provider = Anthropic(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        await llm.chat("Message 1")
        await llm.chat("Message 2")
        
        usage = provider.usage
        assert usage.input_tokens == 25  # 10 + 15
        assert usage.output_tokens == 45  # 20 + 25

@pytest.mark.asyncio
async def test_anthropic_error_handling(config):
    """Test error handling and retries."""
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client
        
        provider = Anthropic(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        with pytest.raises(LLMError) as exc:
            await llm.chat("Hello")
        
        assert "API Error" in str(exc.value)
        assert mock_client.messages.create.call_count >= 1

@pytest.mark.asyncio
async def test_anthropic_timeout(config):
    """Test timeout handling."""
    # Create a base mock response
    mock_resp = type('Response', (), {
        'content': 'Test response',
        'usage': type('Usage', (), {
            'input_tokens': 10,
            'output_tokens': 20
        })
    })()

    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.2)  # Longer than timeout
        raise asyncio.TimeoutError("Operation timed out")
    
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = slow_response
        mock_anthropic.return_value = mock_client
        
        # Use very short timeout
        test_config = {
            "api_key": "test_key",
            "timeout": 0.1,
            "max_retries": 1
        }
        provider = Anthropic(test_config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        with pytest.raises(LLMError) as exc:
            await llm.chat("Hello")
        
        assert "timeout" in str(exc.value).lower()

@pytest.mark.asyncio
async def test_anthropic_token_tracking(config):
    """Test token usage tracking."""
    response1 = type('Response', (), {
        'content': [
            type('Content', (), {
                'text': 'Response 1'
            })()
        ],
        'usage': type('Usage', (), {
            'input_tokens': 10,
            'output_tokens': 20
        })
    })()
    
    response2 = type('Response', (), {
        'content': [
            type('Content', (), {
                'text': 'Response 2'
            })()
        ],
        'usage': type('Usage', (), {
            'input_tokens': 15,
            'output_tokens': 25
        })
    })()
    
    with patch('anthropic.AsyncAnthropic') as mock_anthropic:
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = [response1, response2]
        mock_anthropic.return_value = mock_client
        
        provider = Anthropic(config)
        llm = provider.createLLM("test", "You are a test assistant.")
        
        await llm.chat("Message 1")
        await llm.chat("Message 2")
        
        usage = provider.usage
        assert usage.input_tokens == 25  # 10 + 15
        assert usage.output_tokens == 45  # 20 + 25
