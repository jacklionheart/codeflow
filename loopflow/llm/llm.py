# llm.py
"""
Core abstractions for LLM interactions in loopflow.

This module provides the base interfaces and data structures for working with
large language models, with each LLM instance representing a single conversation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Tuple

class LLMError(Exception):
    """Raised when LLM operations fail."""
    pass

@dataclass
class UsageStats:
    """
    Tracks token usage and associated costs.
    
    Attributes:
        input_tokens: Total tokens in prompts
        output_tokens: Total tokens in completions
    """    
    # For now just using Claude-3.5 Sonnet pricing
    usd_per_1000_input_tokens: float = 0.003
    usd_per_1000_output_tokens: float = 0.015
    input_tokens: int = 0
    output_tokens: int = 0

    def totalCostUsd(self) -> float:
        """Total cost in USD."""
        return self.inputCostUsd() + self.outputCostUsd()
    
    def inputCostUsd(self) -> float:
        """Cost in USD for input tokens."""
        return self.input_tokens * self.usd_per_1000_input_tokens / 1000
    
    def outputCostUsd(self) -> float:
        """Cost in USD for output tokens."""
        return self.output_tokens * self.usd_per_1000_output_tokens / 1000

    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Record usage from a single interaction."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

@dataclass
class Interaction:
    """A single prompt --> response interaction."""
    prompt: str
    response: str

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Providers handle authentication and client setup, while delegating
    actual chat interactions to model instances.
    """
    usage: UsageStats
    def track(self, input_tokens: int, output_tokens: int) -> None:
        """Record usage from a single interaction."""
        self.usage.track(input_tokens, output_tokens)

    @abstractmethod
    def createLLM(self, name: str, system_prompt: str, priorities: str) -> "LLM":
        """Create a new model instance."""
        pass


class LLM(ABC):
    """
    Abstract base class for language models.
    
    Each instance represents a single conversation thread, maintaining
    context between chat calls.
    """

    name: str
    system_prompt: str
    provider: LLMProvider
    priorities: str
    
    def __init__(self, name: str, provider: LLMProvider, system_prompt: str, priorities: str):
        """
        Initialize a model instance.
        
        Args:
            provider: The authenticated provider to use
        """
        self.name = name
        self.provider = provider
        self.history: List[Interaction] = []
        self.system_prompt = system_prompt
        self.priorities = priorities
    async def chat(self, prompt: str) -> str:
        """
        Send a message and get a response, maintaining conversation context.
        
        Args:
            prompt: The user's input message
            
        Returns:
            The model's response
            
        Raises:
            LLMError: If the chat interaction fails
        """
        interaction = Interaction(prompt=prompt, response="")
        response, input_tokens, output_tokens = await self._chat(prompt)
        interaction.response = response

        self.provider.track(input_tokens, output_tokens)
        self.history.append(interaction)
        return response
    
    @abstractmethod
    async def _chat(self, prompt: str) -> Tuple[str, int, int]:
        """
        Execute the actual chat interaction.
        
        Concrete implementations should focus only on the API interaction,
        as history management is handled by the base class.
        
        Args:
            prompt: The user's input message
            
        Returns:
            The model's response
            Input tokens used
            Output tokens used
            
        Raises:
            LLMError: If the chat interaction fails
        """
        pass


