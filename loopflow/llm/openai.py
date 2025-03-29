"""
OpenAI GPT implementation for loopflow.

This module provides the concrete implementation for interacting with
OpenAI's Chat API, with each instance maintaining its own conversation history.
"""

import asyncio
from openai import AsyncOpenAI

from typing import Any, Dict, Tuple
from .llm import LLMProvider, LLM, UsageStats, LLMError

class OpenAI(LLMProvider):
    """Provider implementation for OpenAI's Chat API."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the OpenAI provider."""
        self.config = config
        self.usage = UsageStats(0, 0)
        # Set the API key and provider settings
        self.api_key = config["api_key"]
        self.timeout = config.get("timeout", 600.0)
        self.max_retries = config.get("max_retries", 3)
        print(f"Initializing OpenAI provider with API key: {config}")
        print(f"OpenAI provider initialized with config: {config}")
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
    async def _chat(self, prompt: str) -> Tuple[str, int, int]:
        """
        Execute a chat interaction using OpenAI's Chat API.
        
        Args:
            prompt: The user's input message.
            
        Returns:
            - GPT's response text.
            - Input tokens used.
            - Output tokens used.
            
        Raises:
            LLMError: If the API call fails, with context-specific suggestions.
        """
        try:
            # Build message history: add system prompt (if any), then conversation history, and current prompt.
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            for interaction in self.history:
                messages.append({"role": "user", "content": interaction.prompt})
                messages.append({"role": "assistant", "content": interaction.response})
            messages.append({"role": "user", "content": prompt})

            # Use the model specified in the config; default to "gpt-4o"
            model = self.provider.config.get("model", "gpt-4o")

            response = await self.provider.aclient.chat.completions.create(model=model,
            messages=messages,
            max_tokens=4096,
            timeout=self.provider.timeout)

            # Support both attribute and dict-style access.
            try:
                choices = response.choices
            except AttributeError:
                choices = response["choices"]

            try:
                message_obj = choices[0].message
            except AttributeError:
                message_obj = choices[0]["message"]

            try:
                message_response = message_obj["content"]
            except (TypeError, KeyError):
                raise LLMError("OpenAI API error: Response format invalid.")

            input_tokens = response["usage"]["prompt_tokens"]
            output_tokens = response["usage"]["completion_tokens"]

            return message_response, input_tokens, output_tokens

        except Exception as e:
            error_msg = str(e).lower()
            # Handle specific error types
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
                raise LLMError(f"OpenAI API error: {str(e)}.")
