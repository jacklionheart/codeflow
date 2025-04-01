"""
OpenAI GPT implementation for loopflow.

This module provides the concrete implementation for interacting with
OpenAI's Chat API, with each instance maintaining its own conversation history.
"""

import asyncio
import logging
from typing import Any, Dict, Tuple

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
        logger.info("Initializing OpenAI provider with config: %s", config)
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
        try:
            # Build message history.
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            for interaction in self.history:
                messages.append({"role": "user", "content": interaction.prompt})
                messages.append({"role": "assistant", "content": interaction.response})
            messages.append({"role": "user", "content": prompt})
            logger.debug("OpenAI request messages: %s", messages)
            model = self.provider.config.get("model", "gpt-4o")
            response = await self.provider.aclient.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
                timeout=self.provider.timeout
            )
            logger.debug("OpenAI raw response: %s", response)
            # Try to extract the reply.
            try:
                choices = response.choices
            except AttributeError:
                choices = response["choices"]

            message_response = None
            try:
                # Preferred format: chat completion style.
                message_obj = choices[0].message
                message_response = message_obj["content"]
            except (AttributeError, KeyError, TypeError):
                try:
                    # Fallback: older completion style.
                    message_response = choices[0]["text"]
                except (KeyError, TypeError):
                    logger.error("OpenAI response format error, choices: %s", choices)
                    raise LLMError("OpenAI API error: Response format invalid.")

            input_tokens = response["usage"]["prompt_tokens"]
            output_tokens = response["usage"]["completion_tokens"]

            return message_response, input_tokens, output_tokens

        except Exception as e:
            logger.error(
                "OpenAI API error. Request messages: %s; Exception: %s", messages, e, exc_info=True
            )
            error_msg = str(e).lower()
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
