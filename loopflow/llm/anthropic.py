"""
Anthropic Claude implementation for loopflow.

This module provides the concrete implementation for interacting with
Anthropic's Claude model, with each instance maintaining its own chat context.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import anthropic

from .llm import LLMProvider, LLM, UsageStats, LLMError

logger = logging.getLogger(__name__)

class Anthropic(LLMProvider):
    """Provider implementation for Anthropic's API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Anthropic provider."""
        self.config = config
        self.usage = UsageStats(0, 0)
        
        # Mask API key in logs for security
        logger.info("Initializing Anthropic provider with config: %s", {
            **config, 
            "api_key": f"{config['api_key'][:8]}...{config['api_key'][-4:]}" if config.get("api_key") else None
        })
        
        self.client = anthropic.AsyncAnthropic(
            api_key=config["api_key"],
            timeout=config.get("timeout", 600.0),
            max_retries=config.get("max_retries", 3)
        )
        
        logger.debug("Anthropic client initialized successfully")
    
    def createLLM(self, name: str, system_prompt: str) -> LLM:
        """Create a new model instance."""
        return Claude(name, self, system_prompt)

class Claude(LLM):
    """
    Implementation of Anthropic's Claude model.
    
    Each instance maintains its own conversation history, allowing for
    contextual chat interactions through the same model.
    """

    def __init__(self, name: str, provider: Anthropic, system_prompt: str = ""):
        """Initialize Claude instance."""
        super().__init__(name, provider, system_prompt)
        self.anthropic = provider

    async def _chat(self, messages: List[Dict[str, str]]) -> Tuple[str, int, int]:
        """
        Execute a chat interaction using Claude.
        
        Args:
            prompt: The user's input message
            
        Returns:
            Claude's response text
            Input tokens used
            Output tokens used
            
        Raises:
            LLMError: If the API call fails, with context-specific suggestions
        """
        try:
            logger.debug("Claude request with %d messages", len(messages))
            
            # Make the API request with system as a top-level parameter
            model = self.anthropic.config.get("model", "claude-3-5-sonnet-20241022")
            response = await self.anthropic.client.messages.create(
                model=model,
                system=self.system_prompt if self.system_prompt else None,
                messages=messages,
                max_tokens=4096
            )
            
            logger.debug("Claude response received: %d input tokens, %d output tokens",
                        response.usage.input_tokens, response.usage.output_tokens)
                        
            return response.content[0].text, response.usage.input_tokens, response.usage.output_tokens
            
        except Exception as e:
            logger.error("Claude API error: %s", str(e), exc_info=True)
            
            error_msg = str(e).lower()
            
            # Handle specific error types
            if isinstance(e, asyncio.TimeoutError):
                raise LLMError("Claude API timeout: Request timed out.")
            elif isinstance(e, anthropic.RateLimitError):
                raise LLMError("Claude API rate limit: Consider implementing request throttling.")
            elif "context length" in error_msg:
                raise LLMError("Claude API context length error: Try clearing the conversation history.")
            elif "invalid api key" in error_msg:
                raise LLMError("Claude API authentication error: Check your API key configuration.")
            elif "timeout" in error_msg:
                raise LLMError("Claude API timeout: Request exceeded configured timeout.")
            else:
                # Generic error handling
                raise LLMError(f"Claude API error: {str(e)}.")