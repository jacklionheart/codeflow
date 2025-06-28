"""
OpenAI GPT implementation for codeflow.

This module provides the concrete implementation for interacting with
OpenAI's Chat API, with each instance maintaining its own conversation history.
"""

import asyncio
import logging
from typing import Any, Dict, Tuple, List

from openai import AsyncOpenAI

from .llm import LLM, LLMError, LLMProvider, UsageStats

logger = logging.getLogger(__name__)

class OpenAI(LLMProvider):
    """Provider implementation for OpenAI's Chat API."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the OpenAI provider."""
        self.config = config
        self.usage = UsageStats(0, 0)
        self.api_key = config["api_key"]
        self.timeout = config.get("timeout", 600.0)
        self.max_retries = config.get("max_retries", 3)
        logger.info("Initializing OpenAI provider with config: %s", {
            **config, 
            "api_key": f"{config['api_key'][:8]}...{config['api_key'][-4:]}" if config.get("api_key") else None
        })
        self.aclient = AsyncOpenAI(api_key=config["api_key"])

    def createLLM(self, name: str, system_prompt: str) -> LLM:
        """Create a new OpenAI model instance."""
        return GPT(name, self, system_prompt)

class GPT(LLM):
    """
    Implementation of OpenAI's GPT model.
    
    Each instance maintains its own conversation history, allowing for
    contextual chat interactions through the same model.
    """
    async def _chat(self, messages: List[Dict[str, str]]) -> Tuple[str, int, int]:
        """
        Execute a chat interaction using OpenAI's GPT model.
        
        Args:
            prompt: The user's input message
            
        Returns:
            The model's response
            Input tokens used
            Output tokens used
            
        Raises:
            LLMError: If the API call fails, with context-specific suggestions
        """
        try:           
            logger.debug("OpenAI request messages: %s", messages)
            
            model = self.provider.config.get("model", "gpt-4o")
            response = await self.provider.aclient.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
                timeout=self.provider.timeout
            )
            
            # Access response data using attribute access (modern OpenAI client)
            message_content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            logger.debug("OpenAI response received: %d input tokens, %d output tokens", 
                         input_tokens, output_tokens)

            return message_content, input_tokens, output_tokens

        except Exception as e:
            logger.error("OpenAI API error: %s", str(e), exc_info=True)
            
            error_msg = str(e).lower()
            
            # Handle specific error types with helpful messages
            if isinstance(e, asyncio.TimeoutError):
                raise LLMError("OpenAI API timeout: Request timed out.")
            elif "rate limit" in error_msg:
                raise LLMError("OpenAI API rate limit: Consider implementing request throttling.")
            elif "context" in error_msg:
                raise LLMError("OpenAI API context length error: Try reducing prompt size or clearing conversation history.")
            elif "invalid api key" in error_msg:
                raise LLMError("OpenAI API authentication error: Check your API key configuration.")
            elif "timeout" in error_msg:
                raise LLMError("OpenAI API timeout: Request exceeded configured timeout.")
            else:
                # Generic error handling
                raise LLMError(f"OpenAI API error: {str(e)}.")