"""
Anthropic Claude implementation for loopflow.

This module provides the concrete implementation for interacting with
Anthropic's Claude model, with each instance maintaining its own chat context.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import asyncio
import anthropic
from typing import Any

from .llm import LLMProvider, LLM, UsageStats, LLMError

class Anthropic(LLMProvider):
    """Provider implementation for Anthropic's API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Anthropic provider."""
        self.config = config
        self.usage = UsageStats(0, 0)

        print(f"Initializing Anthropic provider with API key: {config}")
        
        self.client = anthropic.AsyncAnthropic(
            api_key=config["api_key"],
            timeout=config.get("timeout", 600.0),
            max_retries=config.get("max_retries", 3)
        )

        print(f"Anthropic client initialized with API key: {config}")

    
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

    async def _chat(self, prompt: str) -> Tuple[str, int, int]:
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
            # Build message history without system prompt
            messages = []
            for interaction in self.history:
                messages.append({"role": "user", "content": interaction.prompt})
                messages.append({"role": "assistant", "content": interaction.response})
            messages.append({"role": "user", "content": prompt})
            
            # Make the API request with system as a top-level parameter
            response = await self.anthropic.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=self.system_prompt if self.system_prompt else None,
                messages=messages,
                max_tokens=4096
            )
                        
            return response.content[0].text, response.usage.input_tokens, response.usage.output_tokens
            
        except Exception as e:
            error_msg = str(e).lower()
            suggestion = ""
            
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